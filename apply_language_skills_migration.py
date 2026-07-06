import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")

if not db_url or "[YOUR-PASSWORD]" in db_url:
    sys.exit("DATABASE_URL is not set in .env.")

with open(os.path.join(os.path.dirname(__file__), "migrate_language_skills.sql")) as f:
    migration_sql = f.read()

try:
    conn = psycopg2.connect(db_url)
except psycopg2.OperationalError as e:
    sys.exit(f"Could not connect to the database: {e}")

try:
    with conn:
        with conn.cursor() as cur:
            cur.execute(migration_sql)
    print("Language skills migration applied successfully.")
finally:
    conn.close()
