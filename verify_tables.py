import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    sys.exit("Missing SUPABASE_URL or SUPABASE_KEY. Copy .env.example to .env and fill in your project's values.")

supabase = create_client(url, key)

TABLES = [
    "classes",
    "students",
    "objectives",
    "student_objective_status",
    "student_ratings",
    "milestones",
]

all_ok = True
for table in TABLES:
    try:
        supabase.table(table).select("*").limit(1).execute()
        print(f"OK   {table} exists and is queryable")
    except Exception as e:
        all_ok = False
        print(f"FAIL {table}: {e}")

if not all_ok:
    sys.exit("\nOne or more tables are missing. Run create_tables.py first.")

print("\nAll tables are set up correctly.")
