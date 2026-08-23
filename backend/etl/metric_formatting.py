GB_IN_BYTES = 1024**3


def humanize_metric_display(unit: str | None, value: float | None) -> str | None:
    """Converte métricas SNMP de baixo nível pra uma apresentação legível
    (ex.: sys_uptime em ticks -> "1h 2min", storage em bytes -> "2.00 GB").

    Não altera o dado bruto armazenado — só a string de apresentação. None
    quando a unidade não tem conversão definida (a UI cai de volta pro
    value_numeric + metric_unit brutos)."""
    if value is None:
        return None
    if unit == "ticks":
        seconds = int(value / 100)
        hours, remainder = divmod(seconds, 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes}min"
    if unit == "bytes":
        gb = value / GB_IN_BYTES
        return f"{gb:.2f} GB"
    return None
