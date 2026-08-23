"""Testes de humanize_metric_display — não precisam de banco (função pura)."""

from .metric_formatting import humanize_metric_display


def test_ticks_formats_as_hours_and_minutes():
    # 1h 2min = 3720s = 372000 ticks (SNMP TimeTicks = centésimos de segundo)
    assert humanize_metric_display("ticks", 372000) == "1h 2min"


def test_ticks_formats_zero_as_zero_hours_and_minutes():
    assert humanize_metric_display("ticks", 0) == "0h 0min"


def test_bytes_formats_as_gb_with_two_decimals():
    two_gb = 2 * 1024**3
    assert humanize_metric_display("bytes", two_gb) == "2.00 GB"


def test_bytes_formats_fractional_gb():
    half_gb = 0.5 * 1024**3
    assert humanize_metric_display("bytes", half_gb) == "0.50 GB"


def test_unknown_unit_returns_none():
    assert humanize_metric_display("%", 42.0) is None


def test_none_unit_returns_none():
    assert humanize_metric_display(None, 42.0) is None


def test_none_value_returns_none():
    assert humanize_metric_display("ticks", None) is None
