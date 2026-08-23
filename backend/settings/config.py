import os

from dotenv import load_dotenv

load_dotenv()
# Path do arquivo SQLite. Configurável via variável de ambiente DB_PATH
# para não depender de um valor hardcoded espalhado pelo código.
DB_PATH = os.getenv("DB_PATH", "database.db")

# String de conexão Postgres (ex: postgresql+psycopg://user:pass@host:5432/db).
# Quando não definida, o db_connection_handler cai para SQLite local — assim o
# scan de rede continua funcionando sem exigir um Postgres rodando.
DATABASE_URL = os.getenv("DATABASE_URL")

# Setada só pelo conftest.py (pytest_configure), nunca em produção: evita que
# o loop de background (run_forever) rode durante a suíte de testes — ele
# sondaria devices reais concorrentemente com a transação de rollback-por-
# teste, corrompendo a pilha de SAVEPOINT compartilhada.
DISABLE_BACKGROUND_POLLING = os.getenv("DISABLE_BACKGROUND_POLLING") is not None
