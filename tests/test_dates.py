import pytest

from hikvision_downloader.core.dates import (
    build_daily_distribution_xml,
    parse_daily_distribution,
    previous_month,
)


def test_build_daily_distribution_xml_valid() -> None:
    xml = build_daily_distribution_xml(2026, 9)
    assert "<year>2026</year>" in xml
    assert "<monthOfYear>9</monthOfYear>" in xml


def test_build_daily_distribution_xml_invalid() -> None:
    with pytest.raises(ValueError):
        build_daily_distribution_xml(1999, 5)

    with pytest.raises(ValueError):
        build_daily_distribution_xml(2026, 13)


def test_parse_daily_distribution_xml() -> None:
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<dailyDistribution xmlns="http://www.isapi.org/ver20/XMLSchema">
    <day>
        <dayOfMonth>1</dayOfMonth>
        <record>true</record>
    </day>
    <day>
        <dayOfMonth>2</dayOfMonth>
        <record>false</record>
    </day>
    <day>
        <dayOfMonth>15</dayOfMonth>
        <record>true</record>
    </day>
</dailyDistribution>
"""
    dates = parse_daily_distribution(sample_xml, 2026, 9)
    assert len(dates) == 2
    assert dates[0].day == 1
    assert dates[0].iso == "2026-09-01"
    assert dates[1].day == 15
    assert dates[1].iso == "2026-09-15"


def test_previous_month() -> None:
    assert previous_month(2026, 1) == (2025, 12)
    assert previous_month(2026, 9) == (2026, 8)
