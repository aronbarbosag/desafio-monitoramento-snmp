from infra.database.db_connection_handler import db_connection_handler
from repositories.metric_definition_repository import MetricDefinitionRepository
from snmp.oids import build_metric_definitions


def seed_metric_catalog() -> None:
    """Garante que METRIC_CATALOG (snmp/oids.py) está refletido em
    metric_definitions. Chamado no startup da aplicação (main.py)."""
    with db_connection_handler.get_session() as session:
        MetricDefinitionRepository(session).upsert_catalog(build_metric_definitions())
