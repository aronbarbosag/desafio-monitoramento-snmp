import re
from dataclasses import dataclass

from models.enums import MetricValueType


@dataclass(frozen=True)
class DynamicMetricReading:
    """Uma leitura cuja chave/nome nascem em runtime (a partir de um walk
    SNMP), não do catálogo estático — usado por PrinterMetricsService e
    HostResourcesMetricsService."""

    key: str
    name: str
    value_type: MetricValueType
    raw_value: str
    unit: str | None = None


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return slug or "value"


def keyed_readings(
    values: dict[str, str],
    base_key: str,
    base_name: str,
    value_type: MetricValueType,
    unit: str | None = None,
) -> list[DynamicMetricReading]:
    """Um device normalmente tem uma única entrada nessas tabelas (ex: um
    marcador de impressora, uma CPU), aí a chave fica limpa (sem sufixo). Se
    houver mais de uma, desambigua pelo índice descoberto no walk em vez de
    assumir uma quantidade fixa de entradas."""
    if len(values) == 1:
        (_, value) = next(iter(values.items()))
        return [DynamicMetricReading(base_key, base_name, value_type, value, unit)]
    return [
        DynamicMetricReading(
            f"{base_key}_{index.replace('.', '_')}",
            f"{base_name} ({index})",
            value_type,
            value,
            unit,
        )
        for index, value in values.items()
    ]
