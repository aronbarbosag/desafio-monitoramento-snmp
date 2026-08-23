from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    next_cmd,
)

SNMP_PORT = 161


def _clean(value: object) -> str:
    """Alguns agentes SNMP (confirmado: Windows SNMP Service, no ifDescr —
    ex: "Software Loopback Interface 1\x00") retornam OCTET STRING com bytes
    NUL de padding. Postgres rejeita NUL em coluna de texto — limpar aqui, na
    única porta de entrada de todo valor vindo de um walk, protege todo mundo
    rio abaixo (label/name/key derivados, não só o raw_value)."""
    return str(value).replace("\x00", "")


async def walk_column(
    engine: SnmpEngine,
    ip: str,
    community: str,
    column_oid: str,
    timeout: float = 2.0,
    retries: int = 1,
) -> dict[str, str]:
    """SNMP walk (GETNEXT repetido) a partir de column_oid, parando ao sair da
    subtree. Devolve {índice: valor} — o índice é o sufixo do OID retornado
    após column_oid (ex: '1' num escalar de tabela simples, '1.2' num índice
    composto), preservando a indexação real do device em vez de assumir uma
    ordem fixa. Dict vazio = device não suporta essa coluna (não é um erro)."""
    transport = await UdpTransportTarget.create((ip, SNMP_PORT), timeout=timeout, retries=retries)
    current = ObjectIdentity(column_oid)
    results: dict[str, str] = {}
    while True:
        error_indication, error_status, _error_index, var_binds = await next_cmd(
            engine,
            CommunityData(community),
            transport,
            ContextData(),
            ObjectType(current),
        )
        if error_indication or error_status:
            break
        oid, value = var_binds[0]
        oid_str = str(oid)
        if not oid_str.startswith(column_oid + "."):
            break
        index = oid_str[len(column_oid) + 1 :]
        results[index] = _clean(value)
        current = ObjectIdentity(oid_str)
    return results
