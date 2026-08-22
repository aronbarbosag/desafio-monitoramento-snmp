from enum import StrEnum


class DeviceStatus(StrEnum):
    """Estado de disponibilidade de um Device, usado tanto na tabela devices
    (estado atual) quanto em availability_events (histórico de transições)."""

    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"


class MetricValueType(StrEnum):
    """Tipo do valor de uma métrica SNMP, conforme o OID que a origina."""

    INTEGER = "integer"
    COUNTER = "counter"
    GAUGE = "gauge"
    STRING = "string"
