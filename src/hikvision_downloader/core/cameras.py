import tomllib
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

from ..http_client import request_with_retry
from .models import Camera, CameraNumber, TrackId


def format_host_port(host: str, port: int = 80) -> str:
    """Format host and port, including port only when non-80 and not already in host."""
    if ":" in host:
        return host
    if port and port != 80:
        return f"{host}:{port}"
    return host


def parse_video_inputs_xml(xml_text: str) -> list[dict[str, str]]:
    """Parse Hikvision VideoInputChannelList XML into raw channel dictionaries."""
    if not xml_text or not xml_text.strip():
        return []

    root = ET.fromstring(xml_text)
    channels: list[dict[str, str]] = []

    for item in root.iter():
        if not item.tag.endswith("VideoInputChannel"):
            continue

        channel_id: str | None = None
        input_port: str | None = None
        name: str | None = None
        ip_address: str | None = None

        for child in item:
            tag = child.tag.split("}")[-1]
            text = (child.text or "").strip()

            if tag == "id":
                channel_id = text
            elif tag == "inputPort":
                input_port = text
            elif tag == "name":
                name = text
            elif tag in ("ipAddress", "ip"):
                ip_address = text

        effective_id = channel_id or input_port
        if effective_id:
            channels.append(
                {
                    "id": effective_id,
                    "input_port": input_port or effective_id,
                    "name": name or f"Camera_{effective_id}",
                    "ip_address": ip_address or "",
                }
            )

    return channels


def is_meaningful_camera_name(name: str | None) -> bool:
    """Check if the string is a human-meaningful camera name rather than a track/stream number."""
    if not name or not name.strip():
        return False
    cleaned = name.strip()
    lower = cleaned.lower()
    if lower in ("main", "sub", "mainstream", "substream", "video", "audio", "primary", "secondary"):
        return False
    # Disregard pure numeric strings (e.g. "101", "102", "201", "202") as they are track/stream IDs
    return not cleaned.isdigit()


def parse_tracks_xml(xml_text: str) -> tuple[dict[int, dict[str, int]], dict[int, str]]:
    """Parse Hikvision TrackList XML into (tracks_by_channel, channel_names).

    Returns:
        tuple containing:
        - mapping of channel_id -> {'main': track_id, 'sub': track_id, 'third': track_id, ...}
        - mapping of channel_id -> camera name (if present in attributes or elements)
    """
    if not isinstance(xml_text, str) or not xml_text.strip():
        return {}, {}

    root = ET.fromstring(xml_text)
    tracks_by_channel: dict[int, dict[str, int]] = {}
    channel_names: dict[int, str] = {}

    for item in root.iter():
        if not item.tag.endswith("Track"):
            continue

        track_id_str: str | None = None
        input_port_str: str | None = None
        description: str = ""
        extracted_name: str | None = None

        # Check attributes on <Track> tag
        for attr_key, attr_val in item.attrib.items():
            key_lower = attr_key.lower()
            val_clean = attr_val.strip()
            if val_clean and key_lower in ("name", "trackname", "channelname", "cameraname") and is_meaningful_camera_name(val_clean):
                extracted_name = val_clean

        for child in item:
            tag = child.tag.split("}")[-1]
            tag_lower = tag.lower()
            text = (child.text or "").strip()

            if tag in ("id", "trackID"):
                track_id_str = text
            elif tag in ("inputPort", "channelID"):
                input_port_str = text
            elif tag in ("trackDescription", "description", "trackType"):
                description = text.lower()
                if not extracted_name and is_meaningful_camera_name(text):
                    extracted_name = text
            elif tag_lower in ("name", "trackname", "channelname", "cameraname", "devicename") and is_meaningful_camera_name(text):
                extracted_name = text

        if not track_id_str:
            continue

        try:
            track_id_num = int(track_id_str)
        except ValueError:
            continue

        if input_port_str:
            try:
                channel_num = int(input_port_str)
            except ValueError:
                channel_num = track_id_num // 100
        else:
            channel_num = track_id_num // 100

        channel_num = max(channel_num, 1)

        if channel_num not in tracks_by_channel:
            tracks_by_channel[channel_num] = {}

        if extracted_name and is_meaningful_camera_name(extracted_name) and channel_num not in channel_names:
            channel_names[channel_num] = extracted_name

        # Dynamic multi-stream classification: main, sub, third, or custom stream descriptor
        mod = track_id_num % 100
        if "main" in description or mod == 1:
            tracks_by_channel[channel_num]["main"] = track_id_num
        elif "sub" in description or mod == 2:
            tracks_by_channel[channel_num]["sub"] = track_id_num
        elif "third" in description or mod == 3:
            tracks_by_channel[channel_num]["third"] = track_id_num
        else:
            stream_key = description if (description and is_meaningful_camera_name(description)) else f"stream{mod}"
            tracks_by_channel[channel_num][stream_key] = track_id_num

    return tracks_by_channel, channel_names


def parse_streaming_channels_xml(xml_text: str) -> dict[int, str]:
    """Parse Hikvision StreamingChannelList XML to extract camera names by channel number."""
    if not xml_text or not xml_text.strip():
        return {}

    root = ET.fromstring(xml_text)
    names: dict[int, str] = {}

    for item in root.iter():
        if not item.tag.endswith("StreamingChannel"):
            continue

        channel_id_str: str | None = None
        channel_name: str | None = None

        # Check attributes
        for attr_key, attr_val in item.attrib.items():
            if attr_key.lower() in ("name", "channelname") and is_meaningful_camera_name(attr_val):
                channel_name = attr_val.strip()

        for child in item:
            tag = child.tag.split("}")[-1].lower()
            text = (child.text or "").strip()

            if tag in ("id", "channelid"):
                channel_id_str = text
            elif tag in ("channelname", "name", "devicename") and is_meaningful_camera_name(text):
                channel_name = text

        if channel_id_str and channel_name:
            try:
                num = int(channel_id_str)
                channel_num = num // 100 if num >= 100 else num
                is_main_stream = num % 100 == 1 or num < 100
                if channel_num > 0 and (is_main_stream or channel_num not in names):
                    names[channel_num] = channel_name
            except ValueError:
                continue

    return names


def parse_input_proxy_channels_xml(xml_text: str) -> dict[int, dict[str, str]]:
    """Parse Hikvision InputProxyChannelList XML into channel metadata (id, name, ipAddress, model)."""
    if not xml_text or not xml_text.strip():
        return {}

    root = ET.fromstring(xml_text)
    channels: dict[int, dict[str, str]] = {}

    for item in root.iter():
        if not item.tag.endswith("InputProxyChannel"):
            continue

        channel_id: int | None = None
        name: str | None = None
        ip_address: str | None = None
        model: str | None = None

        for child in item:
            tag = child.tag.split("}")[-1]
            text = (child.text or "").strip()

            if tag == "id" and text.isdigit():
                channel_id = int(text)
            elif tag == "name" and text:
                name = text
            elif tag == "sourceInputPortDescriptor":
                for desc_child in child:
                    desc_tag = desc_child.tag.split("}")[-1]
                    desc_text = (desc_child.text or "").strip()
                    if desc_tag in ("ipAddress", "ip") and desc_text:
                        ip_address = desc_text
                    elif desc_tag == "model" and desc_text:
                        model = desc_text

        if channel_id is not None:
            channels[channel_id] = {
                "name": name or "",
                "ip_address": ip_address or "",
                "model": model or "",
            }

    return channels


def parse_input_proxy_status_xml(xml_text: str) -> dict[int, dict[str, object]]:
    """Parse Hikvision InputProxyChannelStatusList XML into status and dynamic multi-track mapping."""
    if not xml_text or not xml_text.strip():
        return {}

    root = ET.fromstring(xml_text)
    status_map: dict[int, dict[str, object]] = {}

    for item in root.iter():
        if not item.tag.endswith("InputProxyChannelStatus"):
            continue

        channel_id: int | None = None
        online = True
        ip_address: str | None = None
        proxy_tracks: list[int] = []

        for child in item:
            tag = child.tag.split("}")[-1]
            text = (child.text or "").strip()

            if tag == "id" and text.isdigit():
                channel_id = int(text)
            elif tag == "online":
                online = text.lower() == "true"
            elif tag == "sourceInputPortDescriptor":
                for desc_child in child:
                    desc_tag = desc_child.tag.split("}")[-1]
                    desc_text = (desc_child.text or "").strip()
                    if desc_tag in ("ipAddress", "ip") and desc_text:
                        ip_address = desc_text
            elif tag == "streamingProxyChannelIdList":
                for trk in child:
                    trk_text = (trk.text or "").strip()
                    if trk_text.isdigit():
                        proxy_tracks.append(int(trk_text))

        if channel_id is not None:
            # Build complete dynamic tracks dictionary for all discovered streams
            stream_tracks: dict[str, int] = {}
            for idx, trk_item in enumerate(proxy_tracks, start=1):
                mod = trk_item % 100
                if mod == 1 or idx == 1:
                    stream_tracks["main"] = trk_item
                elif mod == 2 or idx == 2:
                    stream_tracks["sub"] = trk_item
                elif mod == 3 or idx == 3:
                    stream_tracks["third"] = trk_item
                else:
                    stream_tracks[f"stream{mod}"] = trk_item

            main_track = stream_tracks.get("main", proxy_tracks[0] if proxy_tracks else (channel_id * 100 + 1 if channel_id < 100 else channel_id))
            sub_track = stream_tracks.get("sub", proxy_tracks[1] if len(proxy_tracks) > 1 else (channel_id * 100 + 2 if channel_id < 100 else 0))
            status_map[channel_id] = {
                "online": online,
                "ip_address": ip_address or "",
                "main_track": main_track,
                "sub_track": sub_track,
                "tracks": stream_tracks,
                "proxy_tracks": proxy_tracks,
            }

    return status_map


def discover_cameras_isapi(
    session: requests.Session,
    host: str,
    port: int = 80,
    timeout: float = 120.0,
) -> dict[CameraNumber, Camera]:
    """Execute dynamic camera discovery via Hikvision ISAPI.

    Queries authoritative IP camera endpoints (/ISAPI/ContentMgmt/InputProxy/channels and
    /ISAPI/ContentMgmt/InputProxy/channels/status) to extract real camera names, individual camera
    IP addresses, and all available stream track IDs (main, sub, third, custom). If InputProxy is
    unsupported on the device (e.g. analog/legacy), falls back to /ISAPI/ContentMgmt/record/tracks
    and /ISAPI/Streaming/channels.

    Never silently ignores failures without raising descriptive exceptions.
    """
    host_str = format_host_port(host, port)
    discovery_errors: list[str] = []

    # -------------------------------------------------------------------------
    # 1. Fetch active recording tracks from /ISAPI/ContentMgmt/record/tracks
    # -------------------------------------------------------------------------
    tracks_url = f"http://{host_str}/ISAPI/ContentMgmt/record/tracks"
    tracks_by_channel: dict[int, dict[str, int]] = {}
    track_names: dict[int, str] = {}
    try:
        tracks_resp = request_with_retry(session, "GET", tracks_url, timeout=timeout)
        tracks_by_channel, track_names = parse_tracks_xml(tracks_resp.text)
    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError, TimeoutError, OSError) as trk_err:
        discovery_errors.append(f"Record tracks: {trk_err}")

    # -------------------------------------------------------------------------
    # 2. Fetch camera names and individual IP addresses from InputProxy
    # -------------------------------------------------------------------------
    input_proxy_url = f"http://{host_str}/ISAPI/ContentMgmt/InputProxy/channels"
    status_proxy_url = f"http://{host_str}/ISAPI/ContentMgmt/InputProxy/channels/status"
    channels_data: dict[int, dict[str, str]] = {}
    status_data: dict[int, dict[str, object]] = {}

    try:
        channels_resp = request_with_retry(session, "GET", input_proxy_url, timeout=timeout)
        channels_data = parse_input_proxy_channels_xml(channels_resp.text)
    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError, TimeoutError, OSError) as ip_err:
        discovery_errors.append(f"InputProxy channels: {ip_err}")

    try:
        status_resp = request_with_retry(session, "GET", status_proxy_url, timeout=timeout)
        status_data = parse_input_proxy_status_xml(status_resp.text)
    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError, TimeoutError, OSError) as st_err:
        discovery_errors.append(f"InputProxy status: {st_err}")

    if channels_data:
        cameras: dict[CameraNumber, Camera] = {}
        for ch_id, ch_info in sorted(channels_data.items()):
            ch_num = CameraNumber(ch_id)
            name = ch_info.get("name") or track_names.get(ch_id) or f"Camera_{ch_id}"
            ip_addr = ch_info.get("ip_address") or str(status_data.get(ch_id, {}).get("ip_address", ""))
            model_val = ch_info.get("model") or ""
            if not ip_addr:
                ip_addr = host

            tracks_mapping: dict[str, TrackId] = {}
            if tracks_by_channel.get(ch_id):
                for s_name, s_val in tracks_by_channel[ch_id].items():
                    tracks_mapping[s_name] = TrackId(s_val)

            elif ch_id in status_data:
                st = status_data[ch_id]
                st_tracks_raw = st.get("tracks")
                if isinstance(st_tracks_raw, dict):
                    for s_name, s_val in st_tracks_raw.items():
                        try:
                            tracks_mapping[str(s_name)] = TrackId(int(str(s_val)))
                        except ValueError, TypeError:
                            pass

            if not tracks_mapping:
                tracks_mapping["main"] = TrackId(ch_id * 100 + 1)

            main_track_val = tracks_mapping.get("main", TrackId(ch_id * 100 + 1))
            sub_track_val = tracks_mapping.get("sub", TrackId(0))

            cameras[ch_num] = Camera(
                number=ch_num,
                name=name,
                ip_address=ip_addr,
                model=model_val,
                main_track=main_track_val,
                sub_track=sub_track_val,
                tracks=tracks_mapping,
            )
        return cameras

    # -------------------------------------------------------------------------
    # 3. Strategy 2: ContentMgmt Tracks + Streaming Channels (Legacy / Fallback)
    # -------------------------------------------------------------------------
    streaming_url = f"http://{host_str}/ISAPI/Streaming/channels"
    channel_names: dict[int, str] = dict(track_names)

    try:
        streaming_resp = request_with_retry(session, "GET", streaming_url, timeout=timeout)
        streaming_names = parse_streaming_channels_xml(streaming_resp.text)
        for ch_num_val, s_name in streaming_names.items():
            if ch_num_val not in channel_names or not channel_names[ch_num_val]:
                channel_names[ch_num_val] = s_name
    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError, TimeoutError, OSError) as stream_err:
        discovery_errors.append(f"Streaming channels: {stream_err}")

    if not tracks_by_channel and not channel_names:
        err_msg = "; ".join(discovery_errors) if discovery_errors else "No cameras discovered"
        raise RuntimeError(f"Dynamic camera discovery failed on NVR at {host_str}. Details: {err_msg}")

    fallback_cameras: dict[CameraNumber, Camera] = {}
    all_ch_ids = set(tracks_by_channel.keys()) | set(channel_names.keys())
    for ch_id_val in sorted(all_ch_ids):
        ch_cam_num = CameraNumber(ch_id_val)
        ch_tracks = tracks_by_channel.get(ch_id_val, {})
        tracks_mapping = {k: TrackId(v) for k, v in ch_tracks.items()}
        if "main" not in tracks_mapping:
            tracks_mapping["main"] = TrackId(ch_id_val * 100 + 1)

        main_track = tracks_mapping["main"]
        sub_track = tracks_mapping.get("sub", TrackId(0))
        cam_name = channel_names.get(ch_id_val) or f"Camera_{ch_id_val}"
        fallback_cameras[ch_cam_num] = Camera(
            number=ch_cam_num,
            name=cam_name,
            ip_address=host,
            main_track=main_track,
            sub_track=sub_track,
            tracks=tracks_mapping,
        )

    return fallback_cameras


class CameraDiscoveryService:
    """Maintain an in-memory profile cache for the active session and orchestrate camera discovery."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[CameraNumber, Camera]] = {}

    def get_cache_key(self, host: str, port: int = 80) -> str:
        """Construct cache key for given host and port."""
        return f"{host}:{port}"

    def clear_cache(self) -> None:
        """Clear the in-memory camera discovery profile cache."""
        self._cache.clear()

    def get_cameras(
        self,
        session: requests.Session | None = None,
        host: str | None = None,
        port: int = 80,
        config_file: str | Path | None = None,
        force_refresh: bool = False,
        timeout: float = 120.0,
    ) -> dict[CameraNumber, Camera]:
        """Retrieve cameras from optional TOML override or ISAPI dynamic discovery with cache."""
        if config_file is not None:
            path = Path(config_file)
            if path.exists():
                return load_cameras(path)

        if not host:
            raise ValueError("NVR host must be provided for dynamic camera discovery.")

        if session is None:
            raise ValueError("An authenticated session must be provided for dynamic camera discovery.")

        cache_key = self.get_cache_key(host, port)
        if not force_refresh and cache_key in self._cache:
            return self._cache[cache_key]

        cameras = discover_cameras_isapi(session=session, host=host, port=port, timeout=timeout)
        self._cache[cache_key] = cameras
        return cameras


def load_cameras(config_file: str | Path) -> dict[CameraNumber, Camera]:
    """Load and validate camera configurations from a TOML file (local override)."""
    path = Path(config_file)

    if not path.exists():
        raise FileNotFoundError(f"Camera configuration file not found: {path}\nCopy config/cameras.example.toml to {path} and configure it.")

    with path.open("rb") as file:
        data = tomllib.load(file)

    camera_entries = data.get("cameras")
    if not isinstance(camera_entries, list) or not camera_entries:
        raise ValueError(f"No valid [[cameras]] definitions found in configuration file: {path}")

    cameras: dict[CameraNumber, Camera] = {}
    seen_main_track_ids: set[TrackId] = set()
    seen_sub_track_ids: set[TrackId] = set()
    seen_track_ids: set[TrackId] = set()

    for item in camera_entries:
        if not isinstance(item, dict):
            continue

        camera_number = CameraNumber(int(item["number"]))
        main_track = TrackId(int(item.get("main_track", item["number"] * 100 + 1)))
        sub_track = TrackId(int(item.get("sub_track", 0)))

        tracks_dict: dict[str, TrackId] = {}
        if "tracks" in item and isinstance(item["tracks"], dict):
            for s_name, s_val in item["tracks"].items():
                tracks_dict[str(s_name)] = TrackId(int(s_val))

        if "main" not in tracks_dict and int(main_track) > 0:
            tracks_dict["main"] = main_track
        if "sub" not in tracks_dict and int(sub_track) > 0:
            tracks_dict["sub"] = sub_track

        if camera_number in cameras:
            raise ValueError(f"Duplicate camera number '{camera_number}' found in configuration: {path}")

        if main_track in seen_main_track_ids:
            raise ValueError(f"Duplicate main track ID '{main_track}' assigned to camera {camera_number}")
        seen_main_track_ids.add(main_track)

        if int(sub_track) > 0:
            if sub_track in seen_sub_track_ids:
                raise ValueError(f"Duplicate sub track ID '{sub_track}' assigned to camera {camera_number}")
            seen_sub_track_ids.add(sub_track)

        for s_name, trk in tracks_dict.items():
            if s_name not in ("main", "sub"):
                if trk in seen_track_ids or trk in seen_main_track_ids or trk in seen_sub_track_ids:
                    raise ValueError(f"Duplicate track ID '{trk}' assigned to camera {camera_number}")
                seen_track_ids.add(trk)

        camera = Camera(
            number=camera_number,
            name=str(item["name"]).strip(),
            ip_address=str(item["ip_address"]).strip(),
            model=str(item.get("model", "")).strip(),
            main_track=main_track,
            sub_track=sub_track,
            tracks=tracks_dict,
        )

        cameras[camera.number] = camera

    return cameras
