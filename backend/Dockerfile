FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# iputils-ping: usado por PingSweepService (ver services/ping_sweep_service.py)
# em vez do socket raw do scapy — este precisa resolver o MAC do próximo
# salto por host antes de mandar cada pacote ICMP quando a ARP cache tá fria
# (o comum numa varredura de subnet inteira), o que não termina em tempo
# hábil dentro de um container. O `ping` do SO usa a pilha ICMP do kernel
# direto e não tem esse gargalo.
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala as dependências antes de copiar o código: camada só invalida quando
# pyproject.toml/uv.lock mudam, não a cada edição de código-fonte.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

# O ARP (L2) não enxerga a LAN física do host daqui de dentro. POST
# /devices/scan detecta isso (ARP não acha nada) e cai automaticamente pro
# ping sweep (ICMP/L3, atravessa a bridge do Docker normalmente) — os
# devices achados assim entram sem MAC/fabricante (ver README).
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
