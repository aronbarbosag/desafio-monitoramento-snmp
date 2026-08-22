# Backend

## Requisitos

- Python >= 3.13
- [Npcap](https://npcap.com) — necessário para o `scapy` conseguir enviar/receber pacotes ARP na camada 2. Sem ele, ou é preciso rodar o terminal como Administrador, ou instalar o Npcap com a opção "Restrict Npcap driver's access to Administrators" desmarcada, para rodar sem admin.

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
