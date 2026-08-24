# Backend

## Requisitos

- Python >= 3.11
- [Npcap](https://npcap.com) — necessário para o `scapy` conseguir enviar/receber pacotes ARP na camada 2. Sem ele, ou é preciso rodar o terminal como Administrador, ou instalar o Npcap com a opção "Restrict Npcap driver's access to Administrators" desmarcada, para rodar sem admin.
- Um projeto [Supabase](https://supabase.com) (Postgres gerenciado) — banco padrão do projeto, local e em Docker. Sem `DATABASE_URL` configurada, cai automaticamente pra SQLite local, mas esse não é mais o caminho testado.

## Rodando localmente

```
uv sync
uv run main.py
```

Copie `.env.example` pra `.env` e preencha `DATABASE_URL` com a **connection string do Session Pooler** do seu projeto Supabase (Project Settings → Database → Connection string → aba "Session pooler", porta 5432) — não a de conexão direta (`db.<project>.supabase.co`): ela só resolve por IPv6 hoje e falha em redes sem suporte IPv6 completo. O scheme precisa ser `postgresql+psycopg://` (driver psycopg3), não `postgresql://` puro.

## Rodando via Docker

```
docker compose up --build
```

Sobe só a API (`app`), lendo o mesmo `backend/.env` — não há serviço de Postgres no `docker-compose.yml` porque o banco é o Supabase, externo.

**Descoberta de rede (`POST /devices/scan`) dentro do container: funciona, mas sem MAC.**
`IpScanService` usa ARP (camada 2), que exige acesso direto à LAN física — algo que um container normalmente não tem (no Docker Desktop, Windows/Mac, o container roda numa VM Linux virtualizada e nunca enxerga a placa de rede física real, mesmo com host networking). Quando o ARP não acha nenhum device, `run_ip_and_snmp_scan` cai automaticamente pro `PingSweepService` (ICMP, camada 3) — esse atravessa a bridge do Docker normalmente (NAT/roteamento comuns, sem exigir L2). A resposta do scan indica isso via `used_ping_sweep_fallback: true`; os devices achados nesse modo entram no banco com `mac: null` (`Device.mac` é opcional justamente pra isso — ver `models/device.py`).

Rodando dentro do container, passe o CIDR da LAN física explicitamente — o autodetect enxerga só a rede virtual do container, não a do host:

```
curl -X POST "http://localhost:8000/devices/scan?subnet=192.168.1.0/24"
```

Sem `subnet`, o autodetect roda mesmo assim (útil pra ver o scan funcionando de ponta a ponta, só que sobre a rede virtual do Docker em vez da LAN física).

Se preferir descoberta com MAC/fabricante completos, rode o ARP fora do container, direto no host (onde `scapy` tem acesso real à LAN), agendado periodicamente:

```
DATABASE_URL=<mesma connection string do .env> uv run python composer/registry_devices.py
```

O container também expõe `GET /network/ping-sweep` como diagnóstico isolado ("quem está de pé nessa subnet agora", sem tocar no cadastro de devices):

```
curl "http://localhost:8000/network/ping-sweep?subnet=192.168.1.0/24"
```

## Rodando os testes

Os testes usam um Postgres **descartável** (não o Supabase — nunca escrevem no banco de produção). Suba ele antes de rodar a suíte:

```
docker compose -f ../docker-compose.test.yml up -d --wait
uv run pytest -q
```

`conftest.py` já força `DATABASE_URL` pra esse Postgres local (porta 5433) antes de qualquer teste importar o resto da app, independente do que estiver no `.env`. Cada teste começa com as tabelas zeradas (`TRUNCATE ... CASCADE`) — o Postgres roda com dados em `tmpfs` (RAM), então nem persiste entre restarts do container. Pra rodar também o teste real contra a impressora: `SNMP_TEST_TARGET=192.168.1.214 uv run pytest -q`.

## Estrutura do projeto

```
backend/
├── main.py                # entrypoint da aplicação
├── core/                  # configuração (env vars, paths, etc.)
├── models/                # entidades ORM (SQLAlchemy) — um arquivo por entidade
├── infra/
│   └── database/          # conexão com o banco (engine/session), padrão Strategy
├── repositories/          # acesso a dados (Repository Pattern) por entidade
└── services/              # regras de negócio / casos de uso, com testes colocados
                            # junto do arquivo testado (ex: ip_scan_service.py e
                            # test_ip_scan_service.py na mesma pasta)
```

### Convenções

- Interfaces (classes abstratas) têm o prefixo `I` no nome do arquivo e da classe, ex: `i_connection_strategy.py` → `IConnectionStrategy`.
- Testes ficam ao lado do código que testam, não centralizados numa pasta `tests/`.
