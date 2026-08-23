from .snmp_walk import _clean


def test_clean_strips_embedded_nul_bytes():
    """Regressão: o SNMP Service do Windows retorna ifDescr com um byte NUL
    de padding (ex: "Software Loopback Interface 1\x00") — Postgres rejeita
    NUL em coluna de texto, quebrando o INSERT do MetricDefinition."""
    assert _clean("Software Loopback Interface 1\x00") == "Software Loopback Interface 1"


def test_clean_converts_non_string_values():
    assert _clean(42) == "42"
