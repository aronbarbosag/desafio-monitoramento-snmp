import asyncio
from dataclasses import dataclass

from fastapi import HTTPException

from infra.database.db_connection_handler import db_connection_handler
from models import Base, Device, Subnet
from repositories.device_repository import DeviceRepository
from repositories.subnet_repository import SubnetRepository
from services.ip_scan_service import IpScanService, SubnetTooLargeError
from services.ping_sweep_service import PingSweepService
from services.snmp_scan_service import SnmpScanService


@dataclass(frozen=True)
class ScanSummary:
    subnet: str | None
    devices_found: int
    devices_probed: int
    snmp_identified: int
    used_ping_sweep_fallback: bool = False


async def run_ip_and_snmp_scan(ipscan: bool = True, subnet: str | None = None) -> ScanSummary:
    """SNMPSCAN (identidade) sobre devices SNMP-capable.

    Por padrão (ipscan=True) roda o IPSCAN (ARP na subnet) antes, pra
    descobrir/registrar devices novos, e sonda via SNMP só quem acabou de
    ser achado — mesma sequência do Step 2/3. `subnet` (CIDR, ex:
    "192.168.1.0/24") força a subnet alvo em vez do autodetect — necessário
    quando rodando dentro do Docker, onde o autodetect só enxerga a rede
    virtual do container, não a LAN física do host.

    Se o ARP não devolver nenhum device — o caso comum de dentro de um
    container, sem acesso L2 à LAN física (ver backend/README.md) — cai pro
    PingSweepService (ICMP/L3, atravessa a bridge do Docker normalmente).
    Sem ARP não há como descobrir MAC/fabricante, então os devices achados
    assim entram com mac=None (ver Device.mac e DeviceRepository.upsert_many).

    Com ipscan=False, pula o ARP e sonda direto TODOS os devices que já
    estão no banco (de qualquer subnet/idade) — útil pra re-verificar
    identidade SNMP sem depender de repetir a descoberta de rede toda vez.
    """
    with db_connection_handler.get_session() as session:
        device_repo = DeviceRepository(session)

        if ipscan:
            try:
                ip_scan = IpScanService(subnet)
            except SubnetTooLargeError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            found = await ip_scan.execute()
            subnet_cidr = ip_scan.subnet
            used_ping_sweep_fallback = False

            if not found:
                sweep_results = await PingSweepService(subnet_cidr).execute()
                found = [
                    {"ip": r.ip, "mac": None, "vendor": None} for r in sweep_results if r.online
                ]
                used_ping_sweep_fallback = True

            subnet_row = SubnetRepository(session).save(Subnet(cidr=subnet_cidr))
            target_devices = device_repo.upsert_many(
                [
                    Device(
                        ip=device["ip"],
                        mac=device["mac"],
                        vendor=device["vendor"],
                        subnet_id=subnet_row.id,
                    )
                    for device in found
                ]
            )
            devices_found = len(found)
        else:
            target_devices = device_repo.list_all()
            subnet_cidr = None
            devices_found = 0
            used_ping_sweep_fallback = False

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
                    model_name=result.model_name,
                    sys_contact=result.sys_contact,
                    sys_location=result.sys_location,
                )

    return ScanSummary(
        subnet=subnet_cidr,
        devices_found=devices_found,
        devices_probed=len(target_devices),
        snmp_identified=len(snmp_results),
        used_ping_sweep_fallback=used_ping_sweep_fallback,
    )


if __name__ == "__main__":
    Base.metadata.create_all(db_connection_handler.get_engine())
    summary = asyncio.run(run_ip_and_snmp_scan())
    print(
        f"{summary.devices_found} dispositivo(s) novo(s) salvo(s) para a subnet {summary.subnet} "
        f"({summary.snmp_identified}/{summary.devices_probed} responderam SNMP)"
    )
