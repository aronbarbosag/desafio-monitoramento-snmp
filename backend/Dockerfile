FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Instala as dependências antes de copiar o código: camada só invalida quando
# pyproject.toml/uv.lock mudam, não a cada edição de código-fonte.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

# ipscan=True (ARP) não funciona daqui de dentro — sem acesso L2 à LAN física
# do host. O container faz SNMP/polling contra devices já identificados; a
# descoberta ARP roda separadamente no host (ver README).
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
