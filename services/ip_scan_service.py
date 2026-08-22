import asyncio

from scapy.all import (  # Não há nada de errado nessa importação. Ela está correta.
    ARP,
    Ether,
    conf,
    srp,
)
from scapy.utils import ltoa


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
        self.subnet = ip_subnet or detect_local_subnet()

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

        # Envia e recebe os pacotes. Timeout de 2s e 3 retries para dar chance
        # de responder a dispositivos em economia de energia (ex: celulares
        # com tela desligada) ou que percam o pacote ARP na primeira tentativa,
        # sem deixar o scan todo muito lento quando um IP não responde.

        # colocar verbose =1
        result = srp(packet, timeout=3, retry=3, verbose=0)[0]

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
