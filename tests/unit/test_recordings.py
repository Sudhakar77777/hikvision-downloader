from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from hikvision_downloader.core.models import (
    ByteCount,
    CameraNumber,
    ISODatetimeStr,
    Recording,
    TrackId,
)
from hikvision_downloader.core.recordings import (
    build_search_xml,
    get_all_recordings,
    get_query_value,
    parse_search_response,
    recording_total_size,
    save_recording_list,
    search_recordings,
)


def test_build_search_xml_valid() -> None:
    xml = build_search_xml(
        track_id=TrackId(101),
        start_time="2026-09-15T00:00:00Z",
        end_time="2026-09-15T23:59:59Z",
        position=0,
        batch_size=10,
    )
    assert "<trackID>101</trackID>" in xml
    assert "<maxResults>10</maxResults>" in xml
    assert "<searchResultPostion>0</searchResultPostion>" in xml
    assert "<startTime>2026-09-15T00:00:00Z</startTime>" in xml
    assert "<endTime>2026-09-15T23:59:59Z</endTime>" in xml


def test_build_search_xml_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid track ID"):
        build_search_xml(TrackId(0), "2026-09-15T00:00:00Z", "2026-09-15T23:59:59Z", 0, 10)

    with pytest.raises(ValueError, match="Position cannot be negative"):
        build_search_xml(TrackId(101), "2026-09-15T00:00:00Z", "2026-09-15T23:59:59Z", -1, 10)

    with pytest.raises(ValueError, match="Batch size must be >= 1"):
        build_search_xml(TrackId(101), "2026-09-15T00:00:00Z", "2026-09-15T23:59:59Z", 0, 0)


def test_get_query_value() -> None:
    url = "http://192.168.1.100/ISAPI/ContentMgmt/download?name=ch01.mp4&size=1024"
    assert get_query_value(url, "name") == "ch01.mp4"
    assert get_query_value(url, "size") == "1024"
    assert get_query_value(url, "missing") is None
    assert get_query_value("http://192.168.1.100/test", "key") is None


def test_parse_search_response_from_fixture() -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "cm_search_result.xml"
    xml_content = fixture_path.read_text(encoding="utf-8")

    recordings = parse_search_response(xml_content)
    assert len(recordings) == 2
    assert recordings[0].name == "ch01_20260915_000000.mp4"
    assert recordings[0].start == "2026-09-15T00:00:00Z"
    assert recordings[0].end == "2026-09-15T00:15:00Z"
    assert recordings[0].size_bytes == ByteCount(52428800)
    assert recordings[1].name == "ch01_20260915_001500.mp4"
    assert recordings[1].size_bytes == ByteCount(62914560)


def test_parse_search_response_empty_fixture() -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "cm_search_empty.xml"
    xml_content = fixture_path.read_text(encoding="utf-8")

    recordings = parse_search_response(xml_content)
    assert len(recordings) == 0


def test_parse_search_response_empty_string_and_corrupted() -> None:
    assert parse_search_response("") == []
    assert parse_search_response("   ") == []

    corrupted_item = """<?xml version="1.0" encoding="UTF-8"?>
    <CMSearchResult>
        <matchList>
            <searchMatchItem>
                <startTime>2026-09-15T00:00:00Z</startTime>
                <!-- missing endTime and playbackURI -->
            </searchMatchItem>
        </matchList>
    </CMSearchResult>
    """
    assert parse_search_response(corrupted_item) == []


def test_search_recordings_mocked(mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
    <CMSearchResult xmlns="http://www.isapi.org/ver20/XMLSchema">
        <matchList>
            <searchMatchItem>
                <startTime>2026-09-15T00:00:00Z</startTime>
                <endTime>2026-09-15T00:15:00Z</endTime>
                <playbackURI>rtsp://192.168.1.100/track?name=ch01.mp4&amp;size=1024</playbackURI>
            </searchMatchItem>
        </matchList>
    </CMSearchResult>
    """
    mock_request = mocker.patch("hikvision_downloader.core.recordings.request_with_retry", return_value=mock_response)

    session = MagicMock()
    recordings = search_recordings(
        session=session,
        host="192.168.1.100",
        track_id=TrackId(101),
        recording_date=date(2026, 9, 15),
        position=0,
        batch_size=5,
        timeout=45.0,
    )

    assert len(recordings) == 1
    assert recordings[0].name == "ch01.mp4"
    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[0][0] == session
    assert call_args[0][1] == "POST"
    assert call_args[0][2] == "http://192.168.1.100/ISAPI/ContentMgmt/search"


def test_get_all_recordings_pagination(mocker: MockerFixture) -> None:
    # Page 1 returns 2 items (batch_size=2), Page 2 returns 1 item (< batch_size, so loop terminates)
    rec1 = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01_1.mp4",
        size_bytes=ByteCount(100),
        playback_uri="rtsp://192.168.1.100/track?name=ch01_1.mp4&size=100",
    )
    rec2 = Recording(
        start=ISODatetimeStr("2026-09-15T00:15:00Z"),
        end=ISODatetimeStr("2026-09-15T00:30:00Z"),
        name="ch01_2.mp4",
        size_bytes=ByteCount(200),
        playback_uri="rtsp://192.168.1.100/track?name=ch01_2.mp4&size=200",
    )
    rec3 = Recording(
        start=ISODatetimeStr("2026-09-15T00:30:00Z"),
        end=ISODatetimeStr("2026-09-15T00:45:00Z"),
        name="ch01_3.mp4",
        size_bytes=ByteCount(300),
        playback_uri="rtsp://192.168.1.100/track?name=ch01_3.mp4&size=300",
    )

    def mock_search(
        _session: MagicMock,
        _host: str,
        _track_id: TrackId,
        _recording_date: date,
        position: int,
        batch_size: int = 1,
        timeout: float = 120.0,
    ) -> list[Recording]:
        if position == 0:
            return [rec1, rec2]
        if position == 2:
            return [rec3]
        return []

    mocker.patch("hikvision_downloader.core.recordings.search_recordings", side_effect=mock_search)

    session = MagicMock()
    all_recs = get_all_recordings(
        session=session,
        host="192.168.1.100",
        track_id=TrackId(101),
        recording_date=date(2026, 9, 15),
        batch_size=2,
    )

    assert len(all_recs) == 3
    assert all_recs[0].name == "ch01_1.mp4"
    assert all_recs[1].name == "ch01_2.mp4"
    assert all_recs[2].name == "ch01_3.mp4"


def test_recording_total_size() -> None:
    recs = [
        Recording(
            start=ISODatetimeStr("2026-09-15T00:00:00Z"),
            end=ISODatetimeStr("2026-09-15T00:15:00Z"),
            name="ch01_1.mp4",
            size_bytes=ByteCount(1024),
            playback_uri="rtsp://192.168.1.100/track",
        ),
        Recording(
            start=ISODatetimeStr("2026-09-15T00:15:00Z"),
            end=ISODatetimeStr("2026-09-15T00:30:00Z"),
            name="ch01_2.mp4",
            size_bytes=ByteCount(2048),
            playback_uri="rtsp://192.168.1.100/track",
        ),
    ]
    assert recording_total_size(recs) == ByteCount(3072)
    assert recording_total_size([]) == ByteCount(0)


def test_save_recording_list(tmp_path: Path) -> None:
    recs = [
        Recording(
            start=ISODatetimeStr("2026-09-15T00:00:00Z"),
            end=ISODatetimeStr("2026-09-15T00:15:00Z"),
            name="ch01_1.mp4",
            size_bytes=ByteCount(1000),
            playback_uri="rtsp://192.168.1.100/ch1",
        )
    ]
    csv_file = save_recording_list(
        recordings=recs,
        output_dir=tmp_path / "subfolder",
        camera_number=CameraNumber(1),
        camera_name="MainGate",
        stream_name="HD",
        recording_date=date(2026, 9, 15),
    )

    assert csv_file.exists()
    assert csv_file.name == "2026-09-15_D1_MainGate_HD_recording-list.csv"
    lines = csv_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "number,name,start,end,size,playback_uri"
    assert "1,ch01_1.mp4,2026-09-15T00:00:00Z,2026-09-15T00:15:00Z,1000,rtsp://192.168.1.100/ch1" in lines[1]
