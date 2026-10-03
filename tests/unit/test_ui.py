"""Headless unit tests for PySide6 desktop GUI models, workers, keychain, and widgets."""

import os
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import keyring
import keyring.errors
import pytest
import requests
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QApplication

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
    get_nvr_password,
    save_nvr_password,
)
from hikvision_downloader.ui.main_window import (
    ARIVEDHA_LOGO_SVG_PATH,
    CameraRowWidget,
    MainWindow,
    resolve_default_output_dir,
)
from hikvision_downloader.ui.models import (
    RecordingItem,
    RecordingsTableModel,
    check_disk_space,
    format_iso_display,
    format_size_human,
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
# 2. Keychain Tests
# =============================================================================


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

    # Save with default port 80
    assert save_nvr_password("192.168.1.100", "admin", "secret123", port=80) is True
    assert get_nvr_password("192.168.1.100", "admin", port=80) == "secret123"

    # Save with non-default port
    assert save_nvr_password("192.168.1.100", "admin", "secret8000", port=8000) is True
    assert get_nvr_password("192.168.1.100", "admin", port=8000) == "secret8000"

    # Delete
    assert delete_nvr_password("192.168.1.100", "admin", port=8000) is True
    assert get_nvr_password("192.168.1.100", "admin", port=8000) == "secret123"  # fallback to host:admin


def test_keychain_error_resilience(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_err(*args: object, **kwargs: object) -> None:
        raise keyring.errors.KeyringError("Backend locked")

    monkeypatch.setattr(keyring, "set_password", mock_err)
    monkeypatch.setattr(keyring, "get_password", mock_err)
    monkeypatch.setattr(keyring, "delete_password", mock_err)

    assert save_nvr_password("192.168.1.100", "admin", "pw") is False
    assert get_nvr_password("192.168.1.100", "admin") is None
    assert delete_nvr_password("192.168.1.100", "admin") is False


# =============================================================================
# 3. Table Model Tests
# =============================================================================


def test_table_model_operations(qapp: QApplication, sample_camera: Camera) -> None:
    model = RecordingsTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 8
    assert model.headerData(1, Qt.Orientation.Horizontal) == "Camera"

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

    # Data check
    idx_cam = model.index(0, RecordingsTableModel.COL_CAMERA)
    assert model.data(idx_cam, Qt.ItemDataRole.DisplayRole) == "D1 MainGate"

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
# 4. Worker Signal Tests
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
# 5. UI Widgets & Window Smoke Tests
# =============================================================================


def test_camera_row_widget(qapp: QApplication, sample_camera: Camera) -> None:
    widget = CameraRowWidget(sample_camera)
    assert widget.objectName() == "cameraRow"
    assert widget.is_selected is True
    assert widget.checkbox.text() == "D1 MainGate"

    widget.checkbox.setChecked(False)
    assert widget.is_selected is False


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
    assert window.camera_scroll.minimumHeight() == 240
    assert window.worker_slider.value() >= 1
    assert window.stream_combo.count() == 1
    assert window.footer_device_label.text() == "Disconnected · Ready"
    assert ARIVEDHA_LOGO_SVG_PATH.exists()

    # Populate camera checklist
    window._on_discovery_cameras({CameraNumber(1): sample_camera})
    assert len(window._camera_rows) == 1
    assert window._camera_rows[0].camera.display_name == "D1 MainGate"
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
    window._disconnect_session()
    assert window.connect_btn.text() == "Connect"
    assert window._session is None
    assert window.footer_device_label.text() == "Disconnected · Ready"

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
