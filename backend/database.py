import os

if os.environ.get("DATABASE_URL"):
    from backend.db_postgres import *
else:
    from backend.db_sqlite import *
