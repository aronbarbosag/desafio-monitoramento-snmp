import os

from dotenv import load_dotenv

load_dotenv()
# Path do arquivo SQLite. Configurável via variável de ambiente DB_PATH
# para não depender de um valor hardcoded espalhado pelo código.
DB_PATH = os.getenv("DB_PATH", "database.db")
