"""
Testes de integração do endpoint /devices contra o app FastAPI real e o
banco configurado (SQLite local por padrão) — sem mock de repository/service.

O único ponto mockável de propósito é o POST /devices/scan: ele dispara um
scan ARP real na LAN (via composer.registry_devices.run_ip_and_snmp_scan),
o que tornaria a suíte dependente de Npcap/privilégio de Administrador e da
rede da máquina que roda o teste. Como ele é injetado via Depends(), o teste
troca só essa dependência (não é um mock de biblioteca, é a própria mecânica
de override de dependências do FastAPI) e mantém o resto do fluxo real.
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from composer.registry_devices import ScanSummary, run_ip_and_snmp_scan
from infra.database.db_connection_handler import db_connection_handler
from main import app
from models import Device, DeviceStatus, MetricDefinition, MetricHistory, MetricValueType, Subnet
from repositories.availability_event_repository import AvailabilityEventRepository
from repositories.device_repository import DeviceRepository
from repositories.metric_definition_repository import MetricDefinitionRepository
from repositories.metric_history_repository import MetricHistoryRepository
from repositories.subnet_repository import SubnetRepository


def _seed_device_with_history_and_event() -> int:
    with db_connection_handler.get_session() as session:
        subnet = SubnetRepository(session).save(Subnet(cidr="192.0.2.0/24"))
        device = DeviceRepository(session).save_many(
            [
                Device(
                    ip="192.0.2.10",
                    mac="00:11:22:33:44:55",
                    vendor="Acme",
                    subnet_id=subnet.id,
                    hostname="host-teste",
                    status=DeviceStatus.ONLINE,
                )
            ]
        )[0]

        metric_def = MetricDefinitionRepository(session).list_all()
        if not metric_def:
            metric_def = [
                MetricDefinition(key="sys_uptime", oid="1.3.6.1.2.1.1.3.0", name="Uptime")
            ]
            session.add_all(metric_def)
            session.flush()
        metric_def = metric_def[0]

        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device.id,
                    metric_definition_id=metric_def.id,
                    collected_at=datetime.now(UTC),
                    value_numeric=123.0,
                )
            ]
        )
        AvailabilityEventRepository(session).open_event(
            device.id, DeviceStatus.ONLINE, datetime.now(UTC)
        )
        return device.id


def test_list_and_get_device():
    with TestClient(app) as client:
        device_id = _seed_device_with_history_and_event()

        list_response = client.get("/devices")
        assert list_response.status_code == 200
        assert any(d["id"] == device_id for d in list_response.json())

        detail_response = client.get(f"/devices/{device_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["hostname"] == "host-teste"


def test_get_device_404_for_unknown_id():
    with TestClient(app) as client:
        response = client.get("/devices/999999")

    assert response.status_code == 404


def test_device_history_and_events():
    with TestClient(app) as client:
        device_id = _seed_device_with_history_and_event()

        history_response = client.get(f"/devices/{device_id}/history")
        events_response = client.get(f"/devices/{device_id}/events")

    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 1
    assert history[0]["metric_key"] == "sys_uptime"
    assert history[0]["value_numeric"] == 123.0
    # 123 ticks (centésimos de segundo) = 1.23s -> "0h 0min"
    assert history[0]["display_value"] == "0h 0min"

    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) >= 1
    assert events[0]["status"] == "online"


def test_device_history_display_value_converts_bytes_to_gb():
    with db_connection_handler.get_session() as session:
        subnet = SubnetRepository(session).save(Subnet(cidr="192.0.2.0/24"))
        device = DeviceRepository(session).save_many(
            [Device(ip="192.0.2.20", mac="00:11:22:33:44:66", subnet_id=subnet.id)]
        )[0]
        metric_def = MetricDefinition(
            key="storage_ram_total_bytes",
            oid="1.3.6.1.2.1.25.2.3.1.5.1",
            name="RAM Total",
            value_type=MetricValueType.GAUGE,
            unit="bytes",
        )
        session.add(metric_def)
        session.flush()
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device.id,
                    metric_definition_id=metric_def.id,
                    collected_at=datetime.now(UTC),
                    value_numeric=2 * 1024**3,
                )
            ]
        )
        device_id = device.id

    with TestClient(app) as client:
        response = client.get(f"/devices/{device_id}/history")

    assert response.status_code == 200
    history = response.json()
    assert history[0]["value_numeric"] == 2 * 1024**3
    assert history[0]["display_value"] == "2.00 GB"


def test_history_and_events_404_for_unknown_device():
    with TestClient(app) as client:
        assert client.get("/devices/999999/history").status_code == 404
        assert client.get("/devices/999999/events").status_code == 404


async def _fake_scan(ipscan: bool = True) -> ScanSummary:
    return ScanSummary(
        subnet="192.0.2.0/24" if ipscan else None,
        devices_found=1 if ipscan else 0,
        devices_probed=1,
        snmp_identified=1,
    )


def test_scan_route_returns_summary():
    app.dependency_overrides[run_ip_and_snmp_scan] = _fake_scan
    try:
        with TestClient(app) as client:
            response = client.post("/devices/scan")
    finally:
        app.dependency_overrides.pop(run_ip_and_snmp_scan, None)

    assert response.status_code == 200
    assert response.json() == {
        "subnet": "192.0.2.0/24",
        "devices_found": 1,
        "devices_probed": 1,
        "snmp_identified": 1,
    }


def test_scan_route_forwards_ipscan_query_param():
    """ipscan=false na query deve chegar até a dependency como ipscan=False —
    é essa passagem que permite pular o ARP e sondar direto os devices do
    banco (o comportamento real da função é validado sem HTTP em
    composer/test_registry_devices.py, gated por SNMP_TEST_TARGET)."""
    app.dependency_overrides[run_ip_and_snmp_scan] = _fake_scan
    try:
        with TestClient(app) as client:
            response = client.post("/devices/scan?ipscan=false")
    finally:
        app.dependency_overrides.pop(run_ip_and_snmp_scan, None)

    assert response.status_code == 200
    assert response.json() == {
        "subnet": None,
        "devices_found": 0,
        "devices_probed": 1,
        "snmp_identified": 1,
    }
