from datetime import date
from pathlib import Path

from hikvision_downloader.core.models import (
    ByteCount,
    CameraNumber,
    ISODatetimeStr,
    Recording,
    TrackId,
)
from hikvision_downloader.core.recordings import (
    build_search_xml,
    get_query_value,
    parse_search_response,
    recording_total_size,
    save_recording_list,
)


def test_build_search_xml() -> None:
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


def test_get_query_value() -> None:
    url = "http://192.168.1.100/ISAPI/ContentMgmt/download?name=ch01.mp4&size=1024"
    assert get_query_value(url, "name") == "ch01.mp4"
    assert get_query_value(url, "size") == "1024"
    assert get_query_value(url, "missing") is None


def test_parse_search_response() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<CMSearchResult xmlns="http://www.isapi.org/ver20/XMLSchema">
    <searchMatchItem>
        <startTime>2026-09-15T00:00:00Z</startTime>
        <endTime>2026-09-15T00:15:00Z</endTime>
        <playbackURI>rtsp://192.168.1.100/Streaming/tracks/101?name=ch01_seg1.mp4&amp;size=52428800</playbackURI>
    </searchMatchItem>
    <searchMatchItem>
        <startTime>2026-09-15T00:15:00Z</startTime>
        <endTime>2026-09-15T00:30:00Z</endTime>
        <playbackURI>rtsp://192.168.1.100/Streaming/tracks/101?name=ch01_seg2.mp4&amp;size=52428800</playbackURI>
    </searchMatchItem>
</CMSearchResult>
"""
    recordings = parse_search_response(xml_text)
    assert len(recordings) == 2
    assert recordings[0].name == "ch01_seg1.mp4"
    assert recordings[0].size_bytes == ByteCount(52428800)
    assert recordings[1].name == "ch01_seg2.mp4"


def test_recording_total_size_and_csv_save(tmp_path: Path) -> None:
    recordings = [
        Recording(
            start=ISODatetimeStr("2026-09-15T00:00:00Z"),
            end=ISODatetimeStr("2026-09-15T00:15:00Z"),
            name="ch01_seg1.mp4",
            size_bytes=ByteCount(50000000),
            playback_uri="rtsp://192.168.1.100/ch1",
        ),
        Recording(
            start=ISODatetimeStr("2026-09-15T00:15:00Z"),
            end=ISODatetimeStr("2026-09-15T00:30:00Z"),
            name="ch01_seg2.mp4",
            size_bytes=ByteCount(50000000),
            playback_uri="rtsp://192.168.1.100/ch1",
        ),
    ]

    total = recording_total_size(recordings)
    assert total == ByteCount(100000000)

    csv_path = save_recording_list(
        recordings=recordings,
        output_dir=tmp_path,
        camera_number=CameraNumber(1),
        camera_name="MainGate",
        stream_name="HD",
        recording_date=date(2026, 9, 15),
    )

    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    assert "ch01_seg1.mp4" in content
    assert "ch01_seg2.mp4" in content
