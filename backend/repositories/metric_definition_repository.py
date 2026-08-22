from sqlalchemy.orm import Session

from models.metric_definition import MetricDefinition


class MetricDefinitionRepository:
    """Acesso a dados da entidade MetricDefinition (o catálogo de métricas SNMP)."""

    def __init__(self, session: Session):
        self._session = session

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
