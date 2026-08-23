"""
Testes de integração dos endpoints de analytics/ETL (/devices/{id}/metrics/...,
/devices/{id}/availability, /dashboard/summary) contra o app FastAPI real e o
banco configurado — sem mock, mesmo padrão de test_devices_controller.py.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from infra.database.db_connection_handler import db_connection_handler
from main import app
from models import Device, DeviceStatus, MetricDefinition, MetricHistory, MetricValueType, Subnet
from repositories.availability_event_repository import AvailabilityEventRepository
from repositories.device_repository import DeviceRepository
from repositories.metric_history_repository import MetricHistoryRepository
from repositories.subnet_repository import SubnetRepository


def _seed_device_with_metric_and_event() -> int:
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        subnet = SubnetRepository(session).save(Subnet(cidr="192.0.2.0/24"))
        device = DeviceRepository(session).save_many(
            [
                Device(
                    ip="192.0.2.10",
                    mac="00:11:22:33:44:66",
                    subnet_id=subnet.id,
                    status=DeviceStatus.ONLINE,
                )
            ]
        )[0]
        definition = MetricDefinition(
            key="cpu_load", oid="1.2.3", name="CPU Load", unit="%", value_type=MetricValueType.GAUGE
        )
        session.add(definition)
        session.flush()
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device.id,
                    metric_definition_id=definition.id,
                    collected_at=now - timedelta(minutes=10),
                    value_numeric=42.0,
                )
            ]
        )
        AvailabilityEventRepository(session).open_event(
            device.id, DeviceStatus.ONLINE, now - timedelta(hours=1)
        )
        return device.id


def test_metric_series_returns_points_for_known_metric():
    with TestClient(app) as client:
        device_id = _seed_device_with_metric_and_event()

        response = client.get(f"/devices/{device_id}/metrics/cpu_load/series?range_hours=1")

    assert response.status_code == 200
    body = response.json()
    assert body["metric_key"] == "cpu_load"
    assert body["unit"] == "%"
    assert len(body["points"]) == 1
    assert body["points"][0]["v"] == 42.0


def test_metric_series_returns_empty_points_for_unknown_metric_key():
    with TestClient(app) as client:
        device_id = _seed_device_with_metric_and_event()

        response = client.get(f"/devices/{device_id}/metrics/does_not_exist/series")

    assert response.status_code == 200
    assert response.json()["points"] == []


def test_metric_series_404_for_unknown_device():
    with TestClient(app) as client:
        response = client.get("/devices/999999/metrics/cpu_load/series")

    assert response.status_code == 404


def test_device_availability_returns_summary():
    with TestClient(app) as client:
        device_id = _seed_device_with_metric_and_event()

        response = client.get(f"/devices/{device_id}/availability?range_hours=2")

    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == device_id
    assert body["availability_pct"] > 0


def test_device_availability_404_for_unknown_device():
    with TestClient(app) as client:
        response = client.get("/devices/999999/availability")

    assert response.status_code == 404


def test_dashboard_summary_returns_counts():
    with TestClient(app) as client:
        _seed_device_with_metric_and_event()

        response = client.get("/dashboard/summary?range_hours=2")

    assert response.status_code == 200
    body = response.json()
    assert body["total_devices"] == 1
    assert body["online"] == 1
