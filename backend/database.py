import os

if os.environ.get("DATABASE_URL"):
    from backend.db_postgres import *          # noqa: F401, F403
else:
    from backend.db_sqlite import *            # noqa: F401, F403
