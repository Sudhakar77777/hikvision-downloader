"""Headless unit tests for PySide6 desktop GUI models, workers, keychain, profiles, and widgets."""

import os
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import keyring
import keyring.errors
import pytest
import requests
from PySide6.QtCore import QDate, QSettings, Qt
from PySide6.QtWidgets import QApplication, QLabel

# Guarantee headless offscreen Qt execution for offline test environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from hikvision_downloader.core.models import (
    ByteCount,
    Camera,
    CameraNumber,
    DownloadResult,
    ISODatetimeStr,
    Recording,
    RecordingDate,
    TrackId,
)
from hikvision_downloader.ui.keychain import (
    delete_nvr_password,
    format_account_key,
    get_nvr_credential,
    get_nvr_password,
    parse_account_key,
    save_nvr_password,
)
from hikvision_downloader.ui.main_window import (
    ARIVEDHA_LOGO_SVG_PATH,
    CameraRowWidget,
    MainWindow,
    ProfileComboBox,
    resolve_default_output_dir,
)
from hikvision_downloader.ui.models import (
    CameraItem,
    CamerasTableModel,
    RecordingItem,
    RecordingsTableModel,
    check_disk_space,
    format_iso_display,
    format_size_human,
)
from hikvision_downloader.ui.settings import (
    ProfileMetadata,
    delete_profile_from_settings,
    get_saved_hosts_from_settings,
    get_saved_usernames_from_settings,
    load_profiles_from_settings,
    save_profile_to_settings,
)
from hikvision_downloader.ui.workers import (
    AuthWorker,
    DatesWorker,
    DiscoveryWorker,
    DownloadWorker,
    SearchWorker,
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a headless QApplication instance is active for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


@pytest.fixture
def sample_camera() -> Camera:
    return Camera(
        number=CameraNumber(1),
        name="MainGate",
        ip_address="192.168.1.100",
        main_track=TrackId(101),
        sub_track=TrackId(102),
        tracks={"main": TrackId(101), "sub": TrackId(102)},
    )


@pytest.fixture
def sample_recording_item(sample_camera: Camera) -> RecordingItem:
    rec = Recording(
        start=ISODatetimeStr("2026-10-02T10:00:00Z"),
        end=ISODatetimeStr("2026-10-02T10:15:00Z"),
        name="ch01_20261002_100000.mp4",
        size_bytes=ByteCount(104857600),  # 100 MB
        playback_uri="rtsp://192.168.1.100/Streaming/tracks/101?starttime=20261002T100000Z",
    )
    return RecordingItem(
        recording=rec,
        camera=sample_camera,
        stream="HD",
        track_id=TrackId(101),
        checked=True,
    )


# =============================================================================
# 1. Formatting and Space Validation Tests
# =============================================================================


def test_format_size_human() -> None:
    assert format_size_human(500) == "500 B"
    assert format_size_human(1024 * 50) == "50.0 KB"
    assert format_size_human(1024 * 1024 * 120) == "120.0 MB"
    assert format_size_human(1024 * 1024 * 1024 * 2) == "2.00 GB"


def test_format_iso_display() -> None:
    assert format_iso_display("2026-10-02T14:30:00Z") == "2026-10-02 14:30:00"
    assert format_iso_display("invalid") == "invalid"


def test_check_disk_space_sufficient(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_usage = shutil._ntuple_diskusage(total=10**12, used=10**11, free=500 * 1024 * 1024 * 1024)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: fake_usage)

    has_space, req, free = check_disk_space(tmp_path, required_bytes=1024 * 1024 * 1024)
    assert has_space is True
    assert req == 1024 * 1024 * 1024
    assert free == 500 * 1024 * 1024 * 1024


def test_check_disk_space_insufficient(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_usage = shutil._ntuple_diskusage(total=10**12, used=10**12 - 50 * 1024 * 1024, free=50 * 1024 * 1024)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: fake_usage)

    has_space, _req, free = check_disk_space(tmp_path, required_bytes=200 * 1024 * 1024)
    assert has_space is False
    assert free == 50 * 1024 * 1024


def test_resolve_default_output_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Custom env var set
    custom_dir = tmp_path / "custom_output"
    monkeypatch.setenv("HIKVISION_OUTPUT_DIR", str(custom_dir))
    assert resolve_default_output_dir() == custom_dir.resolve()

    # Empty env var fallback to Downloads/HikvisionArchive
    monkeypatch.delenv("HIKVISION_OUTPUT_DIR", raising=False)
    fallback = resolve_default_output_dir()
    assert fallback.name == "HikvisionArchive"
    assert "Downloads" in str(fallback)


# =============================================================================
# 2. QSettings Storage Tests (No profiles.json)
# =============================================================================


def test_settings_load_save_delete(tmp_path: Path) -> None:
    test_conf = tmp_path / "test_settings.ini"
    test_settings = QSettings(str(test_conf), QSettings.Format.IniFormat)

    # Initially empty
    assert load_profiles_from_settings(test_settings) == []
    assert get_saved_hosts_from_settings(test_settings) == []
    assert get_saved_usernames_from_settings(settings=test_settings) == []

    # Save profile 1
    assert save_profile_to_settings("192.168.1.100", 80, "admin", settings=test_settings) is True
    assert save_profile_to_settings("192.168.1.101", 8000, "operator", settings=test_settings) is True

    profiles = load_profiles_from_settings(test_settings)
    assert len(profiles) == 2
    assert isinstance(profiles[0], ProfileMetadata)
    assert profiles[0].host == "192.168.1.101"
    assert profiles[0].port == 8000
    assert profiles[0].username == "operator"
    assert profiles[1].host == "192.168.1.100"

    hosts = get_saved_hosts_from_settings(test_settings)
    assert hosts == ["192.168.1.101", "192.168.1.100"]

    users = get_saved_usernames_from_settings(host="192.168.1.101", settings=test_settings)
    assert users == ["operator"]

    # Delete profile
    assert delete_profile_from_settings("192.168.1.100", 80, "admin", settings=test_settings) is True
    assert len(load_profiles_from_settings(test_settings)) == 1
    assert delete_profile_from_settings("nonexistent", 80, "admin", settings=test_settings) is False


def test_settings_corrupted_handling(tmp_path: Path) -> None:
    test_conf = tmp_path / "test_bad.ini"
    test_settings = QSettings(str(test_conf), QSettings.Format.IniFormat)
    test_settings.setValue("profiles_metadata", "invalid json content")
    assert load_profiles_from_settings(test_settings) == []


# =============================================================================
# 3. Keychain Tests
# =============================================================================


def test_keychain_parse_account_key() -> None:
    assert parse_account_key("admin@192.168.1.100:8000") == ("admin", "192.168.1.100", 8000)
    assert parse_account_key("admin@192.168.1.100") == ("admin", "192.168.1.100", 80)
    assert parse_account_key("192.168.1.100:8000:admin") == ("admin", "192.168.1.100", 8000)
    assert parse_account_key("") is None
    assert format_account_key("admin", "192.168.1.100", 80) == "admin@192.168.1.100:80"


def test_keychain_save_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}

    def mock_set_password(service: str, account: str, password: str) -> None:
        store[(service, account)] = password

    def mock_get_password(service: str, account: str) -> str | None:
        return store.get((service, account))

    def mock_delete_password(service: str, account: str) -> None:
        store.pop((service, account), None)

    monkeypatch.setattr(keyring, "set_password", mock_set_password)
    monkeypatch.setattr(keyring, "get_password", mock_get_password)
    monkeypatch.setattr(keyring, "delete_password", mock_delete_password)

    # Save with default port 80 -> stored as primary key admin@192.168.1.100:80
    assert save_nvr_password("192.168.1.100", "admin", "secret123", port=80) is True
    assert get_nvr_password("192.168.1.100", "admin", port=80) == "secret123"

    # Save with non-default port
    assert save_nvr_password("192.168.1.100", "admin", "secret8000", port=8000) is True
    assert get_nvr_password("192.168.1.100", "admin", port=8000) == "secret8000"

    # Fallback matching check
    store[("hikvision_downloader", "admin@192.168.1.100:80")] = "fallback_secret"
    delete_nvr_password("192.168.1.100", "admin", port=8000)
    store[("hikvision_downloader", "admin@192.168.1.100:80")] = "fallback_secret"
    assert get_nvr_password("192.168.1.100", "admin", port=8000) == "fallback_secret"


def test_keychain_get_nvr_credential_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {
        ("hikvision_downloader", "remotebuddy@192.168.1.100:80"): "secret_remote",
    }

    monkeypatch.setattr(keyring, "get_password", lambda s, a: store.get((s, a)))

    class FakeCredential:
        username = "remotebuddy@192.168.1.100:80"
        password = "secret_remote"

    monkeypatch.setattr(keyring, "get_credential", lambda s, u: FakeCredential())

    # Exact match
    assert get_nvr_credential("192.168.1.100", "remotebuddy", 80) == ("remotebuddy", "secret_remote")

    # Mismatched user querying host -> discovers remotebuddy
    assert get_nvr_credential("192.168.1.100", "admin", 80) == ("remotebuddy", "secret_remote")


def test_keychain_error_resilience(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_err(*args: object, **kwargs: object) -> None:
        raise keyring.errors.KeyringError("Backend locked")

    monkeypatch.setattr(keyring, "set_password", mock_err)
    monkeypatch.setattr(keyring, "get_password", mock_err)
    monkeypatch.setattr(keyring, "delete_password", mock_err)
    monkeypatch.setattr(keyring, "get_credential", mock_err)

    assert save_nvr_password("192.168.1.100", "admin", "pw") is False
    assert get_nvr_password("192.168.1.100", "admin") is None
    assert get_nvr_credential("192.168.1.100", "admin") is None
    assert delete_nvr_password("192.168.1.100", "admin") is False


# =============================================================================
# 4. Table Model Tests
# =============================================================================


def test_cameras_table_model_operations(qapp: QApplication, sample_camera: Camera) -> None:
    model = CamerasTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 4
    assert model.headerData(1, Qt.Orientation.Horizontal) == "#"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Camera Name"
    assert model.headerData(3, Qt.Orientation.Horizontal) == "Hardware Model"

    cam2 = Camera(
        number=CameraNumber(2),
        name="Backyard",
        ip_address="192.168.1.101",
        model="DS-2CD2043G2-I",
        main_track=TrackId(201),
        sub_track=TrackId(202),
        tracks={"main": TrackId(201), "sub": TrackId(202)},
    )

    model.set_cameras([sample_camera, cam2])
    assert model.rowCount() == 2
    assert len(model.get_selected_cameras()) == 2
    assert len(model.get_all_cameras()) == 2
    assert isinstance(model.get_items()[0], CameraItem)

    # Verify column display data - exact name without "CH01" prefix
    idx_num = model.index(0, CamerasTableModel.COL_NUM)
    assert model.data(idx_num, Qt.ItemDataRole.DisplayRole) == "1"

    idx_name = model.index(0, CamerasTableModel.COL_NAME)
    assert model.data(idx_name, Qt.ItemDataRole.DisplayRole) == "MainGate"

    idx_model = model.index(1, CamerasTableModel.COL_MODEL)
    assert model.data(idx_model, Qt.ItemDataRole.DisplayRole) == "DS-2CD2043G2-I"

    # Toggle checkbox
    idx_check = model.index(0, CamerasTableModel.COL_CHECK)
    assert model.data(idx_check, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
    model.setData(idx_check, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
    assert len(model.get_selected_cameras()) == 1

    # Deselect all and Select all
    model.select_all(False)
    assert len(model.get_selected_cameras()) == 0
    model.select_all(True)
    assert len(model.get_selected_cameras()) == 2

    # Clear
    model.clear()
    assert model.rowCount() == 0


def test_table_model_operations(qapp: QApplication, sample_camera: Camera) -> None:
    model = RecordingsTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 9
    assert model.headerData(0, Qt.Orientation.Horizontal) == ""
    assert model.headerData(1, Qt.Orientation.Horizontal) == "#"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Camera"
    assert model.headerData(3, Qt.Orientation.Horizontal) == "Stream"
    assert model.headerData(4, Qt.Orientation.Horizontal) == "File Name"
    assert model.headerData(5, Qt.Orientation.Horizontal) == "Start Time"
    assert model.headerData(6, Qt.Orientation.Horizontal) == "End Time"
    assert model.headerData(7, Qt.Orientation.Horizontal) == "Size"
    assert model.headerData(8, Qt.Orientation.Horizontal) == "Status"

    rec1 = Recording(
        start=ISODatetimeStr("2026-10-02T10:00:00Z"),
        end=ISODatetimeStr("2026-10-02T10:15:00Z"),
        name="ch01_20261002_100000.mp4",
        size_bytes=ByteCount(100 * 1024 * 1024),
        playback_uri="rtsp://192.168.1.100/1",
    )
    rec2 = Recording(
        start=ISODatetimeStr("2026-10-02T10:15:00Z"),
        end=ISODatetimeStr("2026-10-02T10:30:00Z"),
        name="ch01_20261002_101500.mp4",
        size_bytes=ByteCount(200 * 1024 * 1024),
        playback_uri="rtsp://192.168.1.100/2",
    )

    items = [
        RecordingItem(recording=rec1, camera=sample_camera, stream="HD", track_id=TrackId(101), checked=True),
        RecordingItem(recording=rec2, camera=sample_camera, stream="HD", track_id=TrackId(101), checked=True),
    ]

    model.set_recordings(items)
    assert model.rowCount() == 2
    assert model.get_total_count() == 2
    assert model.get_selected_count() == 2
    assert model.get_total_selected_size() == 300 * 1024 * 1024
    assert model.headerData(0, Qt.Orientation.Vertical) == "1"
    assert model.headerData(1, Qt.Orientation.Vertical) == "2"

    # Data check - Row 0
    idx_num = model.index(0, RecordingsTableModel.COL_NUM)
    assert model.data(idx_num, Qt.ItemDataRole.DisplayRole) == "1"

    idx_cam = model.index(0, RecordingsTableModel.COL_CAMERA)
    assert model.data(idx_cam, Qt.ItemDataRole.DisplayRole) == "MainGate"

    idx_stream = model.index(0, RecordingsTableModel.COL_STREAM)
    assert model.data(idx_stream, Qt.ItemDataRole.DisplayRole) == "HD"

    idx_check = model.index(0, RecordingsTableModel.COL_CHECK)
    assert model.data(idx_check, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked

    # Toggle checkbox
    model.setData(idx_check, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
    assert model.get_selected_count() == 1
    assert model.get_total_selected_size() == 200 * 1024 * 1024

    # Select all / Deselect all
    model.select_all(False)
    assert model.get_selected_count() == 0
    model.select_all(True)
    assert model.get_selected_count() == 2

    # Select range
    model.select_range(1, 1)
    assert model.get_selected_count() == 1
    assert model.get_selected_items()[0].filename == "ch01_20261002_100000.mp4"

    # Status update
    model.update_item_status("ch01_20261002_100000.mp4", "Completed", bytes_downloaded=100 * 1024 * 1024)
    idx_status = model.index(0, RecordingsTableModel.COL_STATUS)
    assert model.data(idx_status, Qt.ItemDataRole.DisplayRole) == "Completed"

    # Sorting
    model.sort(RecordingsTableModel.COL_SIZE, Qt.SortOrder.DescendingOrder)
    assert model.index(0, RecordingsTableModel.COL_FILENAME).data() == "ch01_20261002_101500.mp4"

    model.clear()
    assert model.rowCount() == 0


# =============================================================================
# 5. Worker Signal Tests
# =============================================================================


def test_auth_worker(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    def mock_request(*args: object, **kwargs: object) -> MagicMock:
        return mock_resp

    monkeypatch.setattr("hikvision_downloader.ui.workers.request_with_retry", mock_request)

    worker = AuthWorker("192.168.1.100", 80, "admin", "password123")
    results: list[tuple[bool, str, object]] = []
    worker.signal_finished.connect(lambda s, m, sess: results.append((s, m, sess)))

    worker.run()
    assert len(results) == 1
    assert results[0][0] is True
    assert isinstance(results[0][2], requests.Session)


def test_discovery_worker(qapp: QApplication, sample_camera: Camera, monkeypatch: pytest.MonkeyPatch) -> None:
    session = requests.Session()

    def mock_get_cameras(*args: object, **kwargs: object) -> dict[CameraNumber, Camera]:
        return {CameraNumber(1): sample_camera}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<DeviceInfo><model>DS-7608NI-I2</model><firmwareVersion>V4.50.000</firmwareVersion></DeviceInfo>"

    monkeypatch.setattr(
        "hikvision_downloader.ui.workers.CameraDiscoveryService.get_cameras",
        mock_get_cameras,
    )
    monkeypatch.setattr(
        "hikvision_downloader.ui.workers.request_with_retry",
        lambda *args, **kwargs: mock_resp,
    )

    worker = DiscoveryWorker(session, "192.168.1.100", 80)
    discovered: list[dict[CameraNumber, Camera]] = []
    device_infos: list[dict[str, str]] = []
    worker.signal_cameras.connect(lambda cams: discovered.append(cams))
    worker.signal_device_info.connect(lambda info: device_infos.append(info))

    worker.run()
    assert len(discovered) == 1
    assert CameraNumber(1) in discovered[0]
    assert len(device_infos) == 1
    assert device_infos[0].get("model") == "DS-7608NI-I2"
    assert device_infos[0].get("firmwareVersion") == "V4.50.000"


def test_dates_worker(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    session = requests.Session()
    sample_dates = {(2026, 10): [RecordingDate(year=2026, month=10, day=1), RecordingDate(year=2026, month=10, day=2)]}

    def mock_discover_dates(*args: object, **kwargs: object) -> tuple[dict[tuple[int, int], list[RecordingDate]], float]:
        return sample_dates, 0.1

    monkeypatch.setattr("hikvision_downloader.ui.workers.discover_available_dates", mock_discover_dates)

    worker = DatesWorker(session, "192.168.1.100")
    received_dates: list[dict[tuple[int, int], list[RecordingDate]]] = []
    worker.signal_dates.connect(lambda d: received_dates.append(d))

    worker.run()
    assert len(received_dates) == 1
    assert (2026, 10) in received_dates[0]
    assert len(received_dates[0][(2026, 10)]) == 2


def test_search_worker(qapp: QApplication, sample_camera: Camera, monkeypatch: pytest.MonkeyPatch) -> None:
    session = requests.Session()
    mock_resp = MagicMock()
    mock_resp.text = """<?xml version="1.0" encoding="utf-8"?>
    <CMSearchResult>
        <matchList>
            <searchMatchItem>
                <startTime>2026-10-02T00:00:00Z</startTime>
                <endTime>2026-10-02T00:15:00Z</endTime>
                <playbackURI>rtsp://192.168.1.100/tracks/101?name=ch01_test.mp4&amp;size=52428800</playbackURI>
            </searchMatchItem>
        </matchList>
    </CMSearchResult>"""

    def mock_request(*args: object, **kwargs: object) -> MagicMock:
        return mock_resp

    monkeypatch.setattr("hikvision_downloader.ui.workers.request_with_retry", mock_request)

    worker = SearchWorker(
        session=session,
        host="192.168.1.100",
        port=80,
        camera_queries=[(sample_camera, "HD", TrackId(101))],
        target_date=date(2026, 10, 2),
    )

    found_batches: list[list[Recording]] = []
    total_found: list[int] = []

    worker.signal_camera_recordings.connect(lambda c, s, t, recs: found_batches.append(recs))
    worker.signal_finished.connect(lambda count: total_found.append(count))

    worker.run()
    assert len(found_batches) == 1
    assert len(found_batches[0]) == 1
    assert total_found == [1]


def test_download_worker(
    qapp: QApplication,
    sample_camera: Camera,
    sample_recording_item: RecordingItem,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = requests.Session()

    def mock_download_recording(*args: object, **kwargs: object) -> tuple[bool, float, ByteCount, bool, str | None]:
        dest: Path = kwargs["destination"]  # type: ignore[assignment]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x" * 1024)
        return True, 0.1, ByteCount(1024), False, None

    monkeypatch.setattr("hikvision_downloader.ui.workers.download_recording", mock_download_recording)

    worker = DownloadWorker(
        session=session,
        host="192.168.1.100",
        port=80,
        selected_items=[sample_recording_item],
        output_root=tmp_path,
        max_workers=2,
        save_csv=True,
    )

    completed_files: list[tuple[str, str, bool]] = []
    final_results: list[DownloadResult] = []

    worker.signal_file_completed.connect(lambda f, s, sk: completed_files.append((f, s, sk)))
    worker.signal_finished.connect(lambda res: final_results.append(res))

    worker.run()
    assert len(completed_files) == 1
    assert completed_files[0][1] == "Completed"
    assert len(final_results) == 1
    assert final_results[0].success is True
    assert final_results[0].downloaded_files == 1


# =============================================================================
# 6. UI Widgets & Window Smoke Tests
# =============================================================================


def test_camera_row_widget(qapp: QApplication, sample_camera: Camera) -> None:
    widget = CameraRowWidget(sample_camera)
    assert widget.objectName() == "cameraRow"
    assert widget.is_selected is True
    assert widget.checkbox.text() == "MainGate"

    widget.checkbox.setChecked(False)
    assert widget.is_selected is False

    # Test camera with model number
    cam_with_model = Camera(
        number=CameraNumber(3),
        name="Lobby",
        ip_address="192.168.1.103",
        model="DS-2CD2143G0-I",
        main_track=TrackId(301),
        sub_track=TrackId(302),
        tracks={"main": TrackId(301), "sub": TrackId(302)},
    )
    widget_model = CameraRowWidget(cam_with_model)
    assert widget_model.checkbox.text() == "Lobby"
    assert widget_model.findChild(QLabel) is not None


def test_main_window_instantiation(qapp: QApplication, sample_camera: Camera) -> None:
    window = MainWindow()
    assert window.windowTitle() == "HikVision Downloader"
    assert window.host_input.text() is not None
    assert window.port_input.width() == 50
    assert window.user_input.minimumWidth() >= 115
    assert window.start_hh_combo.width() == 56
    assert window.start_mm_combo.width() == 56
    assert window.left_panel.minimumWidth() >= 410
    assert window.main_splitter.isCollapsible(0) is False
    assert window.cameras_table is not None
    assert window.cameras_table.verticalHeader().isVisible() is False
    assert window.cameras_table.verticalHeader().defaultSectionSize() == 22
    assert window.cameras_table.isSortingEnabled() is True
    assert window.table_view.verticalHeader().isVisible() is False
    assert window.table_view.verticalHeader().defaultSectionSize() == 22
    assert window.minimumWidth() == 1200
    assert window.minimumHeight() == 820
    assert window.status_badge.maximumHeight() == 28
    assert window.theme_btn.width() == 36
    assert window.theme_btn.height() == 28
    assert window.worker_slider.value() >= 1
    assert window.stream_combo.isEnabled() is False
    assert window.search_btn.isEnabled() is False
    assert window.footer_device_label.text() == "Disconnected · Ready"
    assert ARIVEDHA_LOGO_SVG_PATH.exists()
    assert window.discovered_badge.text() == "0 Segments Discovered · 0 B"
    assert window.selected_badge.text() == "0 Selected · 0 B"

    # Initial cameras stack shows placeholder
    assert window.cameras_stack.currentIndex() == 0
    assert "No cameras discovered" in window.cameras_placeholder_label.text()

    # Populate camera checklist
    window._on_discovery_cameras({CameraNumber(1): sample_camera})
    assert len(window._camera_rows) == 1
    assert window._camera_rows[0].display_name == "MainGate"
    assert window.cameras_table.model().rowCount() == 1
    assert window.cameras_stack.currentIndex() == 1
    assert window.stream_combo.isEnabled() is True
    assert window.stream_combo.count() == 2  # Has HD and SD

    # Deselect all cameras check
    window._set_all_cameras_checked(False)
    assert window._camera_rows[0].is_selected is False
    window._set_all_cameras_checked(True)
    assert window._camera_rows[0].is_selected is True

    # Device Info update check
    window._on_device_info_discovered({"model": "DS-7608NI-K2", "firmwareVersion": "V4.30.060"})
    assert "Model: DS-7608NI-K2" in window.footer_device_label.text()
    assert "Firmware: V4.30.060" in window.footer_device_label.text()
    assert "Active Cameras: 1" in window.footer_device_label.text()

    # Theme toggle
    window._toggle_theme()
    assert window._is_dark_theme is False
    window._toggle_theme()
    assert window._is_dark_theme is True

    # Time presets
    window._apply_time_preset("08", "00", "12", "00")
    assert window.start_hh_combo.currentText() == "08"
    assert window.end_hh_combo.currentText() == "12"

    # Connect / Disconnect button state toggle
    assert window.connect_btn.text() == "Connect"
    window._trigger_discovery = MagicMock()
    window._trigger_dates_discovery = MagicMock()
    window._on_auth_finished(True, "Connected", requests.Session())
    assert window.connect_btn.text() == "Disconnect"
    assert window.search_btn.isEnabled() is True

    window._disconnect_session()
    assert window.connect_btn.text() == "Connect"
    assert window._session is None
    assert window.footer_device_label.text() == "Disconnected · Ready"
    assert window.cameras_stack.currentIndex() == 0
    assert window.search_btn.isEnabled() is False
    assert window.stream_combo.isEnabled() is False

    # Calendar dates highlight
    sample_dates = {(2026, 10): [RecordingDate(year=2026, month=10, day=1), RecordingDate(year=2026, month=10, day=2)]}
    window._on_dates_discovered(sample_dates)
    cal = window.date_picker.calendarWidget()
    assert cal is not None
    fmt = cal.dateTextFormat(QDate(2026, 10, 1))
    assert fmt.toolTip() == "Footage Available"

    # Console log high contrast check
    window.log_message("INFO", "Test high contrast logging")
    assert "Test high contrast logging" in window.console_log.toPlainText()


def test_keychain_reactive_autofill(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test reactive autofill when editing connection input fields."""
    monkeypatch.setattr(
        "hikvision_downloader.ui.main_window.get_nvr_password",
        lambda host, user, port: "keychain_secret" if host == "192.168.1.200" and user == "admin" else None,
    )
    monkeypatch.setattr(
        "hikvision_downloader.ui.main_window.get_nvr_credential",
        lambda host, user, port: ("admin", "keychain_secret") if host == "192.168.1.200" else None,
    )

    window = MainWindow()
    window.host_input.setText("192.168.1.200")
    window.user_input.setText("admin")
    window.port_input.setValue(80)
    window._auto_lookup_keychain()

    assert window.password_input.text() == "keychain_secret"
    assert window.remember_cb.isChecked() is True
    assert "Retrieved from OS Keychain" in window.password_input.toolTip()

    # Test username discovery when host changes with blank user
    monkeypatch.setattr(
        "hikvision_downloader.ui.main_window.get_nvr_password",
        lambda host, user, port: None,
    )
    monkeypatch.setattr(
        "hikvision_downloader.ui.main_window.get_nvr_credential",
        lambda host, user, port: ("remotebuddy", "remotebuddy_secret") if host == "192.168.1.200" else None,
    )
    window.user_input.setText("")
    window._auto_lookup_keychain(allow_user_autodiscovery=True)
    assert window.user_input.text() == "remotebuddy"
    assert window.password_input.text() == "remotebuddy_secret"

    # Test typing user manually does not overwrite with autodiscovery
    window.user_input.setText("customuser")
    window._auto_lookup_keychain(allow_user_autodiscovery=False)
    assert window.user_input.text() == "customuser"
    assert window.password_input.text() == ""

    # Test not found clears password
    monkeypatch.setattr("hikvision_downloader.ui.main_window.get_nvr_password", lambda h, u, p: None)
    monkeypatch.setattr("hikvision_downloader.ui.main_window.get_nvr_credential", lambda h, u, p: None)
    window.host_input.setText("192.168.1.250")
    window._auto_lookup_keychain(allow_user_autodiscovery=True)
    assert window.password_input.text() == ""
    assert window.password_input.toolTip() == ""


def test_disconnect_session_complete_purge(qapp: QApplication, sample_camera: Camera) -> None:
    """Test complete purge of camera items, table rows, counters, console, and inputs on session disconnect."""
    window = MainWindow()
    cam2 = Camera(
        number=CameraNumber(2),
        name="Backyard",
        ip_address="192.168.1.101",
        main_track=TrackId(201),
        sub_track=TrackId(202),
        tracks={"main": TrackId(201), "sub": TrackId(202)},
    )
    window._on_discovery_cameras({CameraNumber(1): sample_camera, CameraNumber(2): cam2})
    assert len(window._camera_rows) == 2
    assert window.cameras_table.model().rowCount() == 2
    assert window.cameras_stack.currentIndex() == 1

    # Emulate active inputs, time presets, log console, and password
    window.host_input.setText("192.168.1.100")
    window.user_input.setText("admin")
    window.port_input.setValue(8000)
    window.password_input.setText("temp_pass")
    window.start_hh_combo.setCurrentText("08")
    window.end_hh_combo.setCurrentText("12")
    window.log_message("INFO", "Active session logging...")
    assert "Active session logging..." in window.console_log.toPlainText()

    # Disconnect session
    window._disconnect_session()
    assert len(window._camera_rows) == 0
    assert window.cameras_table.model().rowCount() == 0
    assert window.cameras_stack.currentIndex() == 0
    assert window.discovered_badge.text() == "0 Segments Discovered · 0 B"
    assert window.selected_badge.text() == "0 Selected · 0 B"
    assert window.overall_progress_bar.value() == 0
    assert "Idle" in window.progress_readout.text()
    assert window.footer_device_label.text() == "Disconnected · Ready"
    assert window.host_input.text() == ""
    assert window.user_input.text() == ""
    assert window.port_input.value() == 80
    assert window.password_input.text() == ""
    assert window.start_hh_combo.currentText() == "00"
    assert window.start_mm_combo.currentText() == "00"
    assert window.end_hh_combo.currentText() == "23"
    assert window.end_mm_combo.currentText() == "59"
    assert window.console_log.toPlainText() == ""
    assert window.search_btn.isEnabled() is False
    assert window.start_download_btn.isEnabled() is False
    assert window.stream_combo.isEnabled() is False


def test_user_input_can_be_cleared_without_autofill_recursion(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that deleting or clearing username does not get auto-overwritten by keychain host discovery."""
    monkeypatch.setattr(
        "hikvision_downloader.ui.main_window.get_nvr_password",
        lambda host, user, port: "admin_pass" if user == "admin" else None,
    )
    monkeypatch.setattr(
        "hikvision_downloader.ui.main_window.get_nvr_credential",
        lambda host, user, port: ("admin", "admin_pass") if host == "192.168.1.100" else None,
    )

    window = MainWindow()
    window.host_input.setText("192.168.1.100")
    window.user_input.setText("admin")
    window._auto_lookup_keychain(allow_user_autodiscovery=False)
    assert window.password_input.text() == "admin_pass"

    # User explicitly deletes the username
    window.user_input.setText("")
    window._auto_lookup_keychain(allow_user_autodiscovery=False)

    # Username MUST remain empty and password cleared, not restored to 'admin'
    assert window.user_input.text() == ""
    assert window.password_input.text() == ""



def test_console_3tier_hierarchy_and_progress(qapp: QApplication) -> None:
    """Test 3-tier console structure and telemetry updates."""
    from hikvision_downloader.core.models import DownloadProgress, MegabitsPerSecond

    window = MainWindow()
    assert window.overall_progress_bar.maximumHeight() == 10
    assert "Idle" in window.progress_readout.text()

    # Emulate download progress
    prog = DownloadProgress(
        filename="ch01_20261002_100000.mp4",
        bytes_downloaded=ByteCount(52428800),
        file_size_bytes=ByteCount(104857600),
        speed_mbps=MegabitsPerSecond(24.5),
        elapsed_seconds=10.0,
        current_index=1,
        total_files=2,
        is_completed=False,
        is_skipped=False,
    )
    window._on_download_progress(prog)
    assert window.overall_progress_bar.value() == 25  # (0 + 0.5) / 2 = 25%
    assert "ch01_20261002_100000.mp4" in window.progress_readout.text()
    assert "24.5 Mbps" in window.progress_readout.text()


def test_twin_summary_badges_reactivity(qapp: QApplication, sample_camera: Camera) -> None:
    """Test twin high-contrast badges update dynamically when table rows change."""
    window = MainWindow()

    rec1 = Recording(
        start=ISODatetimeStr("2026-10-02T10:00:00Z"),
        end=ISODatetimeStr("2026-10-02T10:15:00Z"),
        name="ch01_20261002_100000.mp4",
        size_bytes=ByteCount(100 * 1024 * 1024),
        playback_uri="rtsp://192.168.1.100/1",
    )
    rec2 = Recording(
        start=ISODatetimeStr("2026-10-02T10:15:00Z"),
        end=ISODatetimeStr("2026-10-02T10:30:00Z"),
        name="ch01_20261002_101500.mp4",
        size_bytes=ByteCount(200 * 1024 * 1024),
        playback_uri="rtsp://192.168.1.100/2",
    )

    items = [
        RecordingItem(recording=rec1, camera=sample_camera, stream="HD", track_id=TrackId(101), checked=True),
        RecordingItem(recording=rec2, camera=sample_camera, stream="HD", track_id=TrackId(101), checked=True),
    ]

    window._table_model.set_recordings(items)
    assert window.discovered_badge.text() == "2 Segments Discovered · 300.0 MB"
    assert window.selected_badge.text() == "✓ 2 Selected · 300.0 MB"
    assert "38BDF8" in window.selected_badge.styleSheet()

    # Deselect all
    window._table_model.select_all(False)
    assert window.discovered_badge.text() == "2 Segments Discovered · 300.0 MB"
    assert window.selected_badge.text() == "0 Selected · 0 B"
    assert "64748B" in window.selected_badge.styleSheet()

    # Select 1 item
    idx_check = window._table_model.index(0, RecordingsTableModel.COL_CHECK)
    window._table_model.setData(idx_check, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
    assert window.discovered_badge.text() == "2 Segments Discovered · 300.0 MB"
    assert window.selected_badge.text() == "✓ 1 Selected · 100.0 MB"
    assert "38BDF8" in window.selected_badge.styleSheet()


def test_context_menu_credential_removal(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test removing stored profile and OS Keychain credentials via context menu action."""
    deleted_keychain: list[tuple[str, str, int]] = []
    deleted_settings: list[tuple[str, int, str]] = []

    def mock_delete_pw(host: str, user: str, port: int) -> bool:
        deleted_keychain.append((host, user, port))
        return True

    def mock_delete_prof(host: str, port: int, user: str) -> bool:
        deleted_settings.append((host, port, user))
        return True

    monkeypatch.setattr("hikvision_downloader.ui.main_window.delete_nvr_password", mock_delete_pw)
    monkeypatch.setattr("hikvision_downloader.ui.main_window.delete_profile_from_settings", mock_delete_prof)

    window = MainWindow()
    window.host_input.setText("192.168.1.150")
    window.user_input.setText("admin")
    window.port_input.setValue(8000)
    window.password_input.setText("mypassword")
    window.password_input.setToolTip("🔑 Retrieved from OS Keychain")

    window._remove_current_profile_and_credentials()

    assert len(deleted_keychain) == 1
    assert deleted_keychain[0] == ("192.168.1.150", "admin", 8000)
    assert len(deleted_settings) == 1
    assert deleted_settings[0] == ("192.168.1.150", 8000, "admin")
    assert window.password_input.text() == ""
    assert window.password_input.toolTip() == ""


def test_profile_combobox_dynamic_popup_callback(qapp: QApplication) -> None:
    """Test ProfileComboBox executes popup callback before opening dropdown."""
    cb = ProfileComboBox()
    called: list[bool] = []
    cb.set_popup_callback(lambda: called.append(True))
    cb.showPopup()
    assert len(called) == 1


def test_dropdown_dynamic_refresh_and_keychain_loading_after_disconnect(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that after disconnect, clicking dropdown refreshes items and selecting populates keychain password."""
    s = QSettings("Arivedha", "HikVisionDownloader")
    s.clear()
    save_profile_to_settings("192.168.1.64", 80, "admin", settings=s)
    save_profile_to_settings("192.168.1.75", 8000, "operator", settings=s)

    keychain_store = {
        ("192.168.1.64", "admin", 80): "admin_secret_pass",
        ("192.168.1.75", "operator", 8000): "operator_secret_pass",
    }

    monkeypatch.setattr(
        "hikvision_downloader.ui.main_window.get_nvr_password",
        lambda h, u, p: keychain_store.get((h, u, p)),
    )
    monkeypatch.setattr(
        "hikvision_downloader.ui.main_window.get_nvr_credential",
        lambda h, u, p: (u or "admin", keychain_store.get((h, u or "admin", p))),
    )

    window = MainWindow()

    # Emulate active state then disconnect
    window._disconnect_session()
    assert window.host_input.text() == ""
    assert window.user_input.text() == ""
    assert window.password_input.text() == ""
    assert window.host_input.count() == 0

    # User clicks right-side host dropdown (triggers showPopup)
    window.host_input.showPopup()
    assert window.host_input.count() >= 2
    items = [window.host_input.itemText(i) for i in range(window.host_input.count())]
    assert "192.168.1.75" in items
    assert "192.168.1.64" in items

    # User selects 192.168.1.75 from dropdown
    idx = items.index("192.168.1.75")
    window.host_input.setCurrentIndex(idx)
    window.host_input.activated.emit(idx)

    # Verify host, port, user and password auto-filled immediately from Keychain
    assert window.host_input.text() == "192.168.1.75"
    assert window.port_input.value() == 8000
    assert window.user_input.text() == "operator"
    assert window.password_input.text() == "operator_secret_pass"
    assert window.password_input.toolTip() == "🔑 Retrieved from OS Keychain"

    # User clicks right-side user dropdown
    window.user_input.showPopup()
    user_items = [window.user_input.itemText(i) for i in range(window.user_input.count())]
    assert "operator" in user_items

    # Selecting user from user dropdown
    user_idx = user_items.index("operator")
    window.user_input.setCurrentIndex(user_idx)
    window.user_input.activated.emit(user_idx)
    assert window.password_input.text() == "operator_secret_pass"

    # Cleanup
    s.clear()



