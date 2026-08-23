from sqlalchemy.orm import Session

from models.enums import MetricValueType
from models.metric_definition import MetricDefinition


class MetricDefinitionRepository:
    """Acesso a dados da entidade MetricDefinition (o catálogo de métricas SNMP)."""

    def __init__(self, session: Session):
        self._session = session

    def get_or_create(
        self,
        key: str,
        *,
        name: str,
        value_type: MetricValueType,
        unit: str | None = None,
    ) -> MetricDefinition:
        """Como upsert_catalog, mas pra uma definição por vez, descoberta em
        runtime (ex: PrinterMetricsService, onde a chave só existe depois do
        walk contra um device real — não dá pra semear no boot como o
        catálogo estático). oid fica "dynamic": o valor real é resolvido de
        novo a cada ciclo via walk, não há um OID fixo único pra guardar."""
        existing = self._session.query(MetricDefinition).filter_by(key=key).one_or_none()
        if existing:
            return existing
        definition = MetricDefinition(
            key=key, oid="dynamic", name=name, value_type=value_type, unit=unit
        )
        self._session.add(definition)
        self._session.flush()
        return definition

    def upsert_catalog(self, definitions: list[MetricDefinition]) -> None:
        """Garante que o catálogo definido no código está refletido no banco,
        casando por key. Idempotente de propósito: roda a cada boot da
        aplicação, já que o projeto não usa migrations (Step 2)."""
        existing_keys = {key for (key,) in self._session.query(MetricDefinition.key).all()}
        new_definitions = [d for d in definitions if d.key not in existing_keys]
        if new_definitions:
            self._session.add_all(new_definitions)
            self._session.flush()

    def list_all(self) -> list[MetricDefinition]:
        return self._session.query(MetricDefinition).all()
