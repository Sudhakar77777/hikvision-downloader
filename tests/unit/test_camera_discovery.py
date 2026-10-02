from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from hikvision_downloader.core.cameras import (
    CameraDiscoveryService,
    discover_cameras_isapi,
    format_host_port,
    parse_input_proxy_channels_xml,
    parse_input_proxy_status_xml,
    parse_tracks_xml,
    parse_video_inputs_xml,
)
from hikvision_downloader.core.models import CameraNumber, TrackId

SAMPLE_INPUT_PROXY_CHANNELS_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<InputProxyChannelList version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema" size="2">
<InputProxyChannel version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<id>1</id>
<name>MainGate</name>
<sourceInputPortDescriptor>
<ipAddress>192.168.1.217</ipAddress>
<managePortNo>8000</managePortNo>
<model>DS-2CD1023G2-LIU</model>
</sourceInputPortDescriptor>
</InputProxyChannel>
<InputProxyChannel version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<id>2</id>
<name>MainEntrance</name>
<sourceInputPortDescriptor>
<ipAddress>192.168.1.210</ipAddress>
<managePortNo>8000</managePortNo>
<model>DS-2CD1023G2-LIU</model>
</sourceInputPortDescriptor>
</InputProxyChannel>
</InputProxyChannelList>
"""

SAMPLE_INPUT_PROXY_STATUS_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<InputProxyChannelStatusList version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<InputProxyChannelStatus version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<id>1</id>
<online>true</online>
<sourceInputPortDescriptor>
<ipAddress>192.168.1.217</ipAddress>
</sourceInputPortDescriptor>
<streamingProxyChannelIdList>
<streamingProxyChannelId>101</streamingProxyChannelId>
<streamingProxyChannelId>102</streamingProxyChannelId>
</streamingProxyChannelIdList>
</InputProxyChannelStatus>
<InputProxyChannelStatus version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<id>2</id>
<online>true</online>
<sourceInputPortDescriptor>
<ipAddress>192.168.1.210</ipAddress>
</sourceInputPortDescriptor>
<streamingProxyChannelIdList>
<streamingProxyChannelId>201</streamingProxyChannelId>
<streamingProxyChannelId>202</streamingProxyChannelId>
</streamingProxyChannelIdList>
</InputProxyChannelStatus>
</InputProxyChannelStatusList>
"""

SAMPLE_CHANNELS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<VideoInputChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
    <VideoInputChannel xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
        <id>1</id>
        <inputPort>1</inputPort>
        <name>MainGate</name>
        <videoInputEnabled>true</videoInputEnabled>
        <videoFormat>PAL</videoFormat>
    </VideoInputChannel>
    <VideoInputChannel xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
        <id>2</id>
        <inputPort>2</inputPort>
        <name>BackYard</name>
        <videoInputEnabled>true</videoInputEnabled>
        <videoFormat>PAL</videoFormat>
    </VideoInputChannel>
</VideoInputChannelList>
"""

SAMPLE_TRACKS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<TrackList xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
    <Track xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
        <id>101</id>
        <trackDescription>MainStream</trackDescription>
        <trackType>video</trackType>
        <inputPort>1</inputPort>
    </Track>
    <Track xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
        <id>102</id>
        <trackDescription>SubStream</trackDescription>
        <trackType>video</trackType>
        <inputPort>1</inputPort>
    </Track>
    <Track xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
        <id>201</id>
        <trackDescription>MainStream</trackDescription>
        <trackType>video</trackType>
        <inputPort>2</inputPort>
    </Track>
    <Track xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
        <id>202</id>
        <trackDescription>SubStream</trackDescription>
        <trackType>video</trackType>
        <inputPort>2</inputPort>
    </Track>
</TrackList>
"""


SAMPLE_STREAMING_XML = """<?xml version="1.0" encoding="UTF-8"?>
<StreamingChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
    <StreamingChannel xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
        <id>101</id>
        <channelName>MainGate</channelName>
        <enabled>true</enabled>
    </StreamingChannel>
    <StreamingChannel xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0">
        <id>201</id>
        <channelName>BackYard</channelName>
        <enabled>true</enabled>
    </StreamingChannel>
</StreamingChannelList>
"""


def test_parse_input_proxy_channels_xml() -> None:
    channels = parse_input_proxy_channels_xml(SAMPLE_INPUT_PROXY_CHANNELS_XML)
    assert len(channels) == 2
    assert channels[1]["name"] == "MainGate"
    assert channels[1]["ip_address"] == "192.168.1.217"
    assert channels[2]["name"] == "MainEntrance"
    assert channels[2]["ip_address"] == "192.168.1.210"


def test_parse_input_proxy_channels_xml_empty() -> None:
    assert parse_input_proxy_channels_xml("") == {}
    assert parse_input_proxy_channels_xml("   ") == {}


def test_parse_input_proxy_status_xml() -> None:
    status_map = parse_input_proxy_status_xml(SAMPLE_INPUT_PROXY_STATUS_XML)
    assert len(status_map) == 2
    assert status_map[1]["online"] is True
    assert status_map[1]["ip_address"] == "192.168.1.217"
    assert status_map[1]["main_track"] == 101
    assert status_map[1]["sub_track"] == 102
    assert status_map[2]["online"] is True
    assert status_map[2]["ip_address"] == "192.168.1.210"
    assert status_map[2]["main_track"] == 201
    assert status_map[2]["sub_track"] == 202


def test_parse_input_proxy_status_xml_empty() -> None:
    assert parse_input_proxy_status_xml("") == {}
    assert parse_input_proxy_status_xml("   ") == {}


def test_format_host_port() -> None:
    assert format_host_port("192.168.1.100", 80) == "192.168.1.100"
    assert format_host_port("192.168.1.100", 8000) == "192.168.1.100:8000"
    assert format_host_port("192.168.1.100:8000", 80) == "192.168.1.100:8000"
    assert format_host_port("nvr.local", 8888) == "nvr.local:8888"


def test_parse_video_inputs_xml() -> None:
    channels = parse_video_inputs_xml(SAMPLE_CHANNELS_XML)
    assert len(channels) == 2
    assert channels[0]["id"] == "1"
    assert channels[0]["name"] == "MainGate"
    assert channels[1]["id"] == "2"
    assert channels[1]["name"] == "BackYard"


def test_parse_video_inputs_xml_empty() -> None:
    assert parse_video_inputs_xml("") == []
    assert parse_video_inputs_xml("   ") == []


def test_parse_tracks_xml() -> None:
    tracks, names = parse_tracks_xml(SAMPLE_TRACKS_XML)
    assert len(tracks) == 2
    assert isinstance(names, dict)
    assert tracks[1]["main"] == 101
    assert tracks[1]["sub"] == 102
    assert tracks[2]["main"] == 201
    assert tracks[2]["sub"] == 202


def test_parse_tracks_xml_empty() -> None:
    tracks, names = parse_tracks_xml("")
    assert tracks == {}
    assert names == {}


def test_discover_cameras_isapi_input_proxy_success(mocker: MockerFixture) -> None:
    def fake_request(_session: object, _method: str, url: str, **_kwargs: object) -> MagicMock:
        resp = MagicMock()
        if "InputProxy/channels/status" in url:
            resp.text = SAMPLE_INPUT_PROXY_STATUS_XML
        elif "InputProxy/channels" in url:
            resp.text = SAMPLE_INPUT_PROXY_CHANNELS_XML
        return resp

    mocker.patch("hikvision_downloader.core.cameras.request_with_retry", side_effect=fake_request)

    session = MagicMock()
    cameras = discover_cameras_isapi(session, "192.168.1.100", port=8000)

    assert len(cameras) == 2
    assert CameraNumber(1) in cameras
    assert CameraNumber(2) in cameras
    assert cameras[CameraNumber(1)].name == "MainGate"
    assert cameras[CameraNumber(1)].ip_address == "192.168.1.217"
    assert cameras[CameraNumber(1)].main_track == TrackId(101)
    assert cameras[CameraNumber(1)].sub_track == TrackId(102)
    assert cameras[CameraNumber(2)].name == "MainEntrance"
    assert cameras[CameraNumber(2)].ip_address == "192.168.1.210"
    assert cameras[CameraNumber(2)].main_track == TrackId(201)
    assert cameras[CameraNumber(2)].sub_track == TrackId(202)


def test_discover_cameras_isapi_tracks_fallback(mocker: MockerFixture) -> None:
    def fake_request(_session: object, _method: str, url: str, **_kwargs: object) -> MagicMock:
        resp = MagicMock()
        if "record/tracks" in url:
            resp.text = SAMPLE_TRACKS_XML
            return resp
        if "Streaming/channels" in url:
            resp.text = SAMPLE_STREAMING_XML
            return resp
        raise RuntimeError("InputProxy endpoints 404 Not Found")

    mocker.patch("hikvision_downloader.core.cameras.request_with_retry", side_effect=fake_request)

    session = MagicMock()
    cameras = discover_cameras_isapi(session, "192.168.1.100")

    # Should discover from tracks and streaming channels
    assert len(cameras) == 2
    assert cameras[CameraNumber(1)].name == "MainGate"
    assert cameras[CameraNumber(1)].main_track == TrackId(101)
    assert cameras[CameraNumber(1)].sub_track == TrackId(102)


def test_discover_cameras_isapi_failure_raises(mocker: MockerFixture) -> None:
    mocker.patch("hikvision_downloader.core.cameras.request_with_retry", side_effect=RuntimeError("Endpoint failure 500"))

    session = MagicMock()
    with pytest.raises(RuntimeError, match="Dynamic camera discovery failed on NVR"):
        discover_cameras_isapi(session, "192.168.1.100")


def test_camera_discovery_service_caching(mocker: MockerFixture) -> None:
    mock_discover = mocker.patch("hikvision_downloader.core.cameras.discover_cameras_isapi")
    mock_discover.return_value = {
        CameraNumber(1): MagicMock(),
    }

    service = CameraDiscoveryService()
    session = MagicMock()

    # First call - cache miss, triggers discover_cameras_isapi
    res1 = service.get_cameras(session=session, host="192.168.1.100", port=80)
    assert len(res1) == 1
    assert mock_discover.call_count == 1

    # Second call - cache hit, does not call discover_cameras_isapi again
    res2 = service.get_cameras(session=session, host="192.168.1.100", port=80)
    assert len(res2) == 1
    assert mock_discover.call_count == 1

    # Force refresh triggers call
    service.get_cameras(session=session, host="192.168.1.100", port=80, force_refresh=True)
    assert mock_discover.call_count == 2

    # Clear cache and query again
    service.clear_cache()
    service.get_cameras(session=session, host="192.168.1.100", port=80)
    assert mock_discover.call_count == 3


def test_camera_discovery_service_toml_override(tmp_path: Path) -> None:
    config_content = """
[[cameras]]
number = 1
name = "LocalGate"
ip_address = "192.168.1.50"
main_track = 101
sub_track = 102
"""
    config_file = tmp_path / "cameras.toml"
    config_file.write_text(config_content, encoding="utf-8")

    service = CameraDiscoveryService()
    cameras = service.get_cameras(config_file=config_file)
    assert len(cameras) == 1
    assert cameras[CameraNumber(1)].name == "LocalGate"


def test_camera_discovery_service_missing_arguments() -> None:
    service = CameraDiscoveryService()
    with pytest.raises(ValueError, match="NVR host must be provided"):
        service.get_cameras(session=MagicMock(), host=None)

    with pytest.raises(ValueError, match="An authenticated session must be provided"):
        service.get_cameras(session=None, host="192.168.1.100")
