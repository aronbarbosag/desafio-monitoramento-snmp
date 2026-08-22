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
