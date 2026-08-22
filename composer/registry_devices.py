import asyncio

from infra.database.db_connection_handler import db_connection_handler
from models.base import Base
from models.device import Device
from models.subnet import Subnet
from repositories.device_repository import DeviceRepository
from repositories.subnet_repository import SubnetRepository
from services.ip_scan_service import IpScanService

engine = db_connection_handler.get_engine()

Base.metadata.create_all(engine)

# Parte de criacao das tabelas esta ok


# ====================================================


async def main():
    ip_scan = IpScanService()
    devices = await ip_scan.execute()

    with db_connection_handler.get_session() as session:
        subnet_repo = SubnetRepository(session)
        device_repo = DeviceRepository(session)

        subnet = subnet_repo.save(Subnet(cidr=ip_scan.subnet))
        device_repo.save_many(
            [
                Device(
                    ip=device["ip"],
                    mac=device["mac"],
                    vendor=device["vendor"],
                    subnet_id=subnet.id,
                )
                for device in devices
            ]
        )

    print(f"{len(devices)} dispositivo(s) salvo(s) para a subnet {ip_scan.subnet}")


asyncio.run(main())
