from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from hikvision_downloader.core.dates import (
    build_daily_distribution_xml,
    discover_available_dates,
    parse_daily_distribution,
    previous_month,
    search_month,
)
from hikvision_downloader.core.models import RecordingDate, TrackId


def test_build_daily_distribution_xml_valid() -> None:
    xml = build_daily_distribution_xml(2026, 9)
    assert "<year>2026</year>" in xml
    assert "<monthOfYear>9</monthOfYear>" in xml
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml


def test_build_daily_distribution_xml_invalid() -> None:
    with pytest.raises(ValueError, match="Year must be between 2000 and 2100"):
        build_daily_distribution_xml(1999, 5)

    with pytest.raises(ValueError, match="Year must be between 2000 and 2100"):
        build_daily_distribution_xml(2101, 5)

    with pytest.raises(ValueError, match="Month must be between 1 and 12"):
        build_daily_distribution_xml(2026, 0)

    with pytest.raises(ValueError, match="Month must be between 1 and 12"):
        build_daily_distribution_xml(2026, 13)


def test_parse_daily_distribution_from_fixture() -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "daily_distribution.xml"
    xml_content = fixture_path.read_text(encoding="utf-8")

    dates = parse_daily_distribution(xml_content, 2026, 9)
    assert len(dates) == 3
    assert dates[0] == RecordingDate(year=2026, month=9, day=1)
    assert dates[1] == RecordingDate(year=2026, month=9, day=15)
    assert dates[2] == RecordingDate(year=2026, month=9, day=28)


def test_parse_daily_distribution_empty_and_corrupt() -> None:
    assert parse_daily_distribution("", 2026, 9) == []
    assert parse_daily_distribution("   ", 2026, 9) == []

    corrupt_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <dailyDistribution>
        <day>
            <dayOfMonth>invalid_number</dayOfMonth>
            <record>true</record>
        </day>
        <day>
            <dayOfMonth>10</dayOfMonth>
            <record>true</record>
        </day>
    </dailyDistribution>
    """
    dates = parse_daily_distribution(corrupt_xml, 2026, 9)
    assert len(dates) == 1
    assert dates[0].day == 10


def test_previous_month() -> None:
    assert previous_month(2026, 1) == (2025, 12)
    assert previous_month(2026, 9) == (2026, 8)
    assert previous_month(2026, 12) == (2026, 11)


def test_search_month_invalid_track() -> None:
    session = MagicMock()
    with pytest.raises(ValueError, match="Invalid track ID"):
        search_month(session, "192.168.1.100", TrackId(0), 2026, 9)


def test_search_month_mocked(mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
    <dailyDistribution xmlns="http://www.isapi.org/ver20/XMLSchema">
        <day>
            <dayOfMonth>5</dayOfMonth>
            <record>true</record>
        </day>
    </dailyDistribution>
    """
    mock_request = mocker.patch("hikvision_downloader.core.dates.request_with_retry", return_value=mock_response)

    session = MagicMock()
    dates = search_month(session, "192.168.1.100", TrackId(101), 2026, 9, timeout=30.0)

    assert len(dates) == 1
    assert dates[0] == RecordingDate(year=2026, month=9, day=5)

    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[0][0] == session
    assert call_args[0][1] == "POST"
    assert call_args[0][2] == "http://192.168.1.100/ISAPI/ContentMgmt/record/tracks/101/dailyDistribution"


def test_discover_available_dates_two_months(mocker: MockerFixture) -> None:
    # When previous month has no recordings, only current and previous month are queried
    def mock_search(
        _session: MagicMock,
        _host: str,
        _track_id: TrackId,
        year: int,
        month: int,
        timeout: float = 120.0,
    ) -> list[RecordingDate]:
        if year == 2026 and month == 9:
            return [RecordingDate(year=2026, month=9, day=15)]
        return []

    mocker.patch("hikvision_downloader.core.dates.search_month", side_effect=mock_search)

    session = MagicMock()
    results, duration = discover_available_dates(
        session=session,
        host="192.168.1.100",
        discovery_track_id=TrackId(101),
        today=date(2026, 9, 15),
    )

    assert len(results) == 2
    assert (2026, 9) in results
    assert (2026, 8) in results
    assert len(results[(2026, 9)]) == 1
    assert len(results[(2026, 8)]) == 0
    assert duration >= 0.0


def test_discover_available_dates_three_months(mocker: MockerFixture) -> None:
    # When previous month HAS recordings, an older 3rd month is queried
    def mock_search(
        _session: MagicMock,
        _host: str,
        _track_id: TrackId,
        year: int,
        month: int,
        timeout: float = 120.0,
    ) -> list[RecordingDate]:
        if year == 2026 and month == 9:
            return [RecordingDate(year=2026, month=9, day=15)]
        if year == 2026 and month == 8:
            return [RecordingDate(year=2026, month=8, day=20)]
        if year == 2026 and month == 7:
            return [RecordingDate(year=2026, month=7, day=10)]
        return []

    mocker.patch("hikvision_downloader.core.dates.search_month", side_effect=mock_search)

    session = MagicMock()
    results, duration = discover_available_dates(
        session=session,
        host="192.168.1.100",
        discovery_track_id=TrackId(101),
        today=date(2026, 9, 15),
    )

    assert len(results) == 3
    assert (2026, 9) in results
    assert (2026, 8) in results
    assert (2026, 7) in results
    assert len(results[(2026, 9)]) == 1
    assert len(results[(2026, 8)]) == 1
    assert len(results[(2026, 7)]) == 1
    assert duration >= 0.0
