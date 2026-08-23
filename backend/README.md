# Backend

## Requisitos

- Python >= 3.11
- [Npcap](https://npcap.com) — necessário para o `scapy` conseguir enviar/receber pacotes ARP na camada 2. Sem ele, ou é preciso rodar o terminal como Administrador, ou instalar o Npcap com a opção "Restrict Npcap driver's access to Administrators" desmarcada, para rodar sem admin.
- Um projeto [Supabase](https://supabase.com) (Postgres gerenciado) — banco padrão do projeto, local e em Docker. Sem `DATABASE_URL` configurada, cai automaticamente pra SQLite local, mas esse não é mais o caminho testado.

## Rodando localmente

```
uv sync
uv run uvicorn main:app --reload
```

Copie `.env.example` pra `.env` e preencha `DATABASE_URL` com a **connection string do Session Pooler** do seu projeto Supabase (Project Settings → Database → Connection string → aba "Session pooler", porta 5432) — não a de conexão direta (`db.<project>.supabase.co`): ela só resolve por IPv6 hoje e falha em redes sem suporte IPv6 completo. O scheme precisa ser `postgresql+psycopg://` (driver psycopg3), não `postgresql://` puro.

## Rodando via Docker

```
docker compose up --build
```

Sobe só a API (`app`), lendo o mesmo `backend/.env` — não há serviço de Postgres no `docker-compose.yml` porque o banco é o Supabase, externo.

**Importante — descoberta de rede (ARP/IPSCAN) não funciona dentro do container.** `IpScanService` usa `scapy` pra mandar ARP bruto, o que exige acesso de camada 2 à LAN física. Isso não é uma limitação do Docker em si (em Linux bare metal funciona com `network_mode: host` + `cap_add: [NET_RAW, NET_ADMIN]`), mas no Docker Desktop (Windows/Mac) o container roda dentro de uma VM Linux virtualizada e nunca enxerga a placa de rede física real, mesmo com host networking.

Padrão recomendado: rode o ARP fora do container, direto no host (onde `scapy` tem acesso real à LAN), agendado periodicamente:

```
DATABASE_URL=<mesma connection string do .env> uv run python composer/registry_devices.py
```

Isso popula o Supabase com devices novos (ARP + SNMP). O container só faz SNMP/polling contra o que já está no banco (`run_forever`, que nunca chama ARP) — funciona normalmente de dentro do Docker, já que é tráfego UDP comum, sem exigir L2.

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
