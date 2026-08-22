import asyncio

from infra.database.db_connection_handler import db_connection_handler
from models import Base, Device, Subnet
from repositories.device_repository import DeviceRepository
from repositories.subnet_repository import SubnetRepository
from services.ip_scan_service import IpScanService
from services.snmp_scan_service import SnmpScanService

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
        saved_devices = device_repo.save_many(
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

        # IPSCAN achou quem está na rede; SNMPSCAN descobre quem, entre esses,
        # fala SNMP — só quem responde ganha identidade (hostname/sys_descr).
        snmp_results = {
            result.ip: result
            for result in await SnmpScanService().execute([d.ip for d in saved_devices])
        }
        for device in saved_devices:
            if result := snmp_results.get(device.ip):
                device_repo.update_snmp_info(
                    device.id,
                    hostname=result.sys_name,
                    sys_descr=result.sys_descr,
                    sys_object_id=result.sys_object_id,
                    snmp_community=result.community,
                )

    print(
        f"{len(devices)} dispositivo(s) salvo(s) para a subnet {ip_scan.subnet} "
        f"({len(snmp_results)} responderam SNMP)"
    )


asyncio.run(main())
