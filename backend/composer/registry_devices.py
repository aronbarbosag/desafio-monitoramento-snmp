import asyncio
from dataclasses import dataclass

from infra.database.db_connection_handler import db_connection_handler
from models import Base, Device, Subnet
from repositories.device_repository import DeviceRepository
from repositories.subnet_repository import SubnetRepository
from services.ip_scan_service import IpScanService
from services.snmp_scan_service import SnmpScanService


@dataclass(frozen=True)
class ScanSummary:
    subnet: str | None
    devices_found: int
    devices_probed: int
    snmp_identified: int


async def run_ip_and_snmp_scan(ipscan: bool = True) -> ScanSummary:
    """SNMPSCAN (identidade) sobre devices SNMP-capable.

    Por padrão (ipscan=True) roda o IPSCAN (ARP na subnet) antes, pra
    descobrir/registrar devices novos, e sonda via SNMP só quem acabou de
    ser achado — mesma sequência do Step 2/3.

    Com ipscan=False, pula o ARP e sonda direto TODOS os devices que já
    estão no banco (de qualquer subnet/idade) — útil pra re-verificar
    identidade SNMP sem depender de repetir a descoberta de rede toda vez.
    """
    with db_connection_handler.get_session() as session:
        device_repo = DeviceRepository(session)

        if ipscan:
            ip_scan = IpScanService()
            devices = await ip_scan.execute()

            subnet = SubnetRepository(session).save(Subnet(cidr=ip_scan.subnet))
            target_devices = device_repo.save_many(
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
            subnet_cidr = ip_scan.subnet
            devices_found = len(devices)
        else:
            target_devices = device_repo.list_all()
            subnet_cidr = None
            devices_found = 0

        # SNMPSCAN descobre quem, entre os devices alvo, fala SNMP — só quem
        # responde ganha/atualiza identidade (hostname/sys_descr).
        snmp_results = {
            result.ip: result
            for result in await SnmpScanService().execute([d.ip for d in target_devices])
        }
        for device in target_devices:
            if result := snmp_results.get(device.ip):
                device_repo.update_snmp_info(
                    device.id,
                    hostname=result.sys_name,
                    sys_descr=result.sys_descr,
                    sys_object_id=result.sys_object_id,
                    snmp_community=result.community,
                )

    return ScanSummary(
        subnet=subnet_cidr,
        devices_found=devices_found,
        devices_probed=len(target_devices),
        snmp_identified=len(snmp_results),
    )


if __name__ == "__main__":
    Base.metadata.create_all(db_connection_handler.get_engine())
    summary = asyncio.run(run_ip_and_snmp_scan())
    print(
        f"{summary.devices_found} dispositivo(s) novo(s) salvo(s) para a subnet {summary.subnet} "
        f"({summary.snmp_identified}/{summary.devices_probed} responderam SNMP)"
    )
