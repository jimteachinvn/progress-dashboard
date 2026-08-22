"""Schema health check.

Uses the direct Postgres connection, not the publishable key: anon is
deliberately denied table access (see rls_policies.sql), so checking with the
anon client would report healthy tables as "missing".
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if not db_url or "[YOUR-PASSWORD]" in db_url:
    sys.exit("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")

TABLES = ["classes", "students", "student_ratings", "milestones"]

# The six communication criteria the app grades on, plus homework.
RATING_COLUMNS = [
    "fluency_rating",
    "clarity_volume_rating",
    "confidence_willingness_rating",
    "interactive_engagement_rating",
    "vocabulary_application_rating",
    "sentence_construction_rating",
    "homework_rating",
    "notes",
]

conn = psycopg2.connect(db_url)
all_ok = True

with conn.cursor() as cur:
    for table in TABLES:
        cur.execute("select to_regclass(%s)", (f"public.{table}",))
        exists = cur.fetchone()[0] is not None
        if exists:
            cur.execute(f"select count(*) from {table}")
            print(f"OK   {table} exists ({cur.fetchone()[0]} rows)")
        else:
            all_ok = False
            print(f"FAIL {table} is missing")

    cur.execute(
        "select column_name from information_schema.columns "
        "where table_schema = 'public' and table_name = 'student_ratings'"
    )
    present = {r[0] for r in cur.fetchall()}
    for col in RATING_COLUMNS:
        if col in present:
            print(f"OK   student_ratings.{col}")
        else:
            all_ok = False
            print(f"FAIL student_ratings.{col} is missing")

    # The parent portal reads exclusively through this function.
    cur.execute("select to_regprocedure('public.get_student_portal(text)')")
    if cur.fetchone()[0] is not None:
        print("OK   get_student_portal(text) exists")
    else:
        all_ok = False
        print("FAIL get_student_portal(text) is missing")

    cur.execute("select to_regclass('public.student_ratings_one_per_day')")
    if cur.fetchone()[0] is not None:
        print("OK   one-check-in-per-student-per-day index in place")
    else:
        all_ok = False
        print("FAIL student_ratings_one_per_day index is missing")

conn.close()

if not all_ok:
    sys.exit("\nSchema is incomplete. Run create_tables.py, then the apply_*.py migrations.")

print("\nSchema is healthy.")
