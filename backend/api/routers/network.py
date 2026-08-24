import ipaddress

from fastapi import APIRouter, HTTPException

from api.schemas import PingSweepResultOut
from services.ip_scan_service import SubnetTooLargeError, detect_scannable_subnet
from services.ping_sweep_service import PingSweepService

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/ping-sweep")
async def ping_sweep(subnet: str | None = None) -> PingSweepResultOut:
    """Varredura ICMP (L3) de uma subnet — funciona de dentro do container,
    ao contrário do IPSCAN (ARP/L2, ver POST /devices/scan).

    Sem `subnet`, o autodetect resolve a rota default — dentro do Docker
    isso é a rede virtual do container, não a LAN física do host; se ela for
    grande demais pra escanear rápido (ex: a /16 que o Compose atribui por
    padrão ao projeto), corta automaticamente pro /24 ao redor do IP local
    (ver detect_scannable_subnet). Pra varrer a LAN física de verdade,
    informe o CIDR dela explicitamente (ex: `192.168.1.0/24`)."""
    target_subnet = subnet or detect_scannable_subnet()
    try:
        results = await PingSweepService(target_subnet).execute()
    except SubnetTooLargeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    online = sorted((r.ip for r in results if r.online), key=lambda ip: ipaddress.ip_address(ip))
    return PingSweepResultOut(subnet=target_subnet, checked=len(results), online=online)
