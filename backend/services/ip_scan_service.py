import asyncio
import ipaddress

from scapy.all import (  # Não há nada de errado nessa importação. Ela está correta.
    ARP,
    Ether,
    conf,
    srp,
)
from scapy.utils import ltoa

# scapy monta um pacote por host antes de mandar em lote (srp()/sr()) — acima
# disso a montagem sozinha já leva minutos, antes mesmo do envio. Uma LAN
# doméstica/empresarial comum (/24 = 254 hosts) nunca chega perto disso; quem
# estoura é a subnet /16 que o Docker Compose atribui por padrão à rede do
# projeto (65534 hosts) — ver detect_scannable_subnet().
MAX_SCAN_HOSTS = 4096


class SubnetTooLargeError(ValueError):
    """Subnet grande demais pra escanear em tempo hábil (ver MAX_SCAN_HOSTS)."""

    def __init__(self, subnet: str, host_count: int):
        super().__init__(
            f"subnet {subnet} tem {host_count} endereços — acima do limite de "
            f"{MAX_SCAN_HOSTS} pra um scan em tempo hábil. Informe uma subnet "
            "mais específica (ex: a LAN física em /24, não a rede virtual do "
            "Docker)."
        )
        self.subnet = subnet
        self.host_count = host_count


def _check_scan_size(subnet: str) -> None:
    host_count = ipaddress.ip_network(subnet, strict=False).num_addresses
    if host_count > MAX_SCAN_HOSTS:
        raise SubnetTooLargeError(subnet, host_count)


def detect_local_subnet() -> str:
    """
    Descobre dinamicamente a subnet da interface que atende a rota default
    da máquina (ex: '192.168.1.0/24'). Usada quando nenhuma subnet é passada
    explicitamente, para o serviço funcionar em qualquer host/servidor sem
    configuração manual.
    """
    _iface, local_ip, _gateway = conf.route.route("0.0.0.0")

    for network, netmask, _gateway, _iface, output_ip, _metric in conf.route.routes:
        if output_ip != local_ip:
            continue
        # Ignora rota default (máscara 0) e rotas de host (máscara /32).
        if netmask in (0, 0xFFFFFFFF):
            continue
        prefix = bin(netmask).count("1")
        return f"{ltoa(network)}/{prefix}"

    raise RuntimeError(f"não foi possível deduzir a subnet local de {local_ip}")


def detect_scannable_subnet() -> str:
    """Como detect_local_subnet(), mas corta pro /24 ao redor do IP local
    quando a subnet detectada estoura MAX_SCAN_HOSTS — o caso de dentro de um
    container Docker, onde a rota default aponta pra rede /16 que o Compose
    atribui por padrão ao projeto. Só entra em ação no autodetect: uma subnet
    passada explicitamente que seja grande demais é rejeitada com
    SubnetTooLargeError em vez de silenciosamente cortada (ver IpScanService)."""
    subnet = detect_local_subnet()
    if ipaddress.ip_network(subnet, strict=False).num_addresses <= MAX_SCAN_HOSTS:
        return subnet
    _iface, local_ip, _gateway = conf.route.route("0.0.0.0")
    return str(ipaddress.ip_network(f"{local_ip}/24", strict=False))


class IpScanService:
    """
    Service class to perform network scanning using ARP requests on a specified IP subnet.
    Discovers active devices (IP, MAC and fabricante) present on the local network.

    Attributes:
        subnet (str): The IP subnet to scan (e.g., '192.168.1.0/24'). Se não for
            informada, é detectada automaticamente a partir da rota default.

    Methods:
        __perform_scan():
            Synchronously sends ARP requests and collects responses to identify active devices.
        execute():
            Asynchronously runs the blocking network scan in a background thread.

    """

    def __init__(self, ip_subnet: str | None = None):
        self.subnet = ip_subnet or detect_scannable_subnet()
        _check_scan_size(self.subnet)

    def __resolve_vendor(self, mac: str):
        """Descobre o fabricante da placa de rede a partir do OUI do MAC."""
        vendor = conf.manufdb._get_manuf(mac)
        # Quando o OUI não está na base, a lib devolve o próprio MAC de volta.
        if vendor.lower() == mac.lower():
            return None
        return vendor

    def __perform_scan(self) -> list[dict]:
        """Método síncrono que faz o trabalho pesado de rede."""
        # Cria um pacote ARP perguntando "Quem tem esse IP?"
        arp_request = ARP(pdst=self.subnet)
        # Cria um pacote Ethernet para enviar em broadcast (para todos)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp_request

        # Envia e recebe os pacotes. ARP numa LAN saudável responde em poucos
        # ms; timeout=1s + 1 retry já cobre um pacote perdido na primeira
        # tentativa sem deixar o scan todo lento esperando por IPs mortos
        # (era timeout=3/retry=3 — até ~12s de espera numa /24 cheia de IPs
        # que nunca respondem; isso sozinho já cortou o scan de referência de
        # ~12s pra ~2s).
        result = srp(packet, timeout=1, retry=1, verbose=0)[0]

        # Processa as respostas para extrair os IPs e MACs ativos,
        # enriquecendo com o fabricante da placa de rede (OUI do MAC).
        active_devices = []
        for _sent, received in result:
            active_devices.append(
                {
                    "ip": received.psrc,
                    "mac": received.hwsrc,
                    "vendor": self.__resolve_vendor(received.hwsrc),
                },
            )
        return active_devices

    # def __call__(self, *args: Any, **kwds: Any) -> Any:
    #     return self.execute()

    async def execute(self):
        """Método assíncrono que será chamado pelo Controller/Composer."""
        # Roda a função de rede bloqueante em uma thread separada
        return await asyncio.to_thread(self.__perform_scan)
