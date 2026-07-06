import os
import sys

import psycopg2
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
db_url = os.environ.get("DATABASE_URL")

supabase = create_client(url, key)
conn = psycopg2.connect(db_url)
conn.autocommit = True

ok = True


def check(label, cond):
    global ok
    print(f"{'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        ok = False


# 1. anon must NOT be able to read the students table directly.
try:
    res = supabase.table("students").select("*").execute()
    check("anon blocked from reading students directly", len(res.data) == 0)
except Exception:
    check("anon blocked from reading students directly", True)

# 2. RPC with a bogus token returns nothing.
res = supabase.rpc("get_student_portal", {"p_access_token": "not-a-real-token"}).execute()
check("RPC returns null for an unknown token", res.data is None)

# 3. Create a real class/student/objective/status/rating/milestone as postgres
#    (bypasses RLS), then confirm the RPC returns exactly that student's data
#    for the real token, then clean everything up.
with conn.cursor() as cur:
    cur.execute("insert into classes (name, level) values ('RLS Test Class', 'A2') returning id")
    class_id = cur.fetchone()[0]

    cur.execute(
        "insert into students (class_id, name) values (%s, 'RLS Test Student') returning id, access_token",
        (class_id,),
    )
    student_id, access_token = cur.fetchone()

    cur.execute(
        "insert into objectives (class_id, category, title, order_index) "
        "values (%s, 'Speaking', 'Order coffee', 1) returning id",
        (class_id,),
    )
    objective_id = cur.fetchone()[0]

    cur.execute(
        "insert into student_objective_status (student_id, objective_id, status) values (%s, %s, 'in_progress')",
        (student_id, objective_id),
    )
    cur.execute(
        "insert into student_ratings "
        "(student_id, pronunciation_rating, confidence_rating, participation_rating, homework_rating, "
        "listening_rating, reading_rating, writing_rating, grammar_rating, vocabulary_rating) "
        "values (%s, 3, 5, 4, 2, 4, 3, 2, 3, 4)",
        (student_id,),
    )
    cur.execute(
        "insert into milestones (student_id, title) values (%s, 'Finished unit 1')",
        (student_id,),
    )

try:
    res = supabase.rpc("get_student_portal", {"p_access_token": access_token}).execute()
    data = res.data
    check("RPC returns data for the real token", data is not None)
    if data:
        check("student name matches", data["student"]["name"] == "RLS Test Student")
        check("objective + status present", len(data["objectives"]) == 1 and data["objectives"][0]["status"] == "in_progress")
        check(
            "rating present",
            len(data["ratings"]) == 1
            and data["ratings"][0]["pronunciation_rating"] == 3
            and data["ratings"][0]["participation_rating"] == 4
            and data["ratings"][0]["homework_rating"] == 2
            and data["ratings"][0]["listening_rating"] == 4
            and data["ratings"][0]["reading_rating"] == 3
            and data["ratings"][0]["writing_rating"] == 2
            and data["ratings"][0]["grammar_rating"] == 3
            and data["ratings"][0]["vocabulary_rating"] == 4,
        )
        check("milestone present", len(data["milestones"]) == 1 and data["milestones"][0]["title"] == "Finished unit 1")

    # anon still cannot see this row directly even though it has a real token
    try:
        res2 = supabase.table("students").select("*").eq("id", student_id).execute()
        check("anon still blocked from direct table select on the same row", len(res2.data) == 0)
    except Exception:
        check("anon still blocked from direct table select on the same row", True)
finally:
    with conn.cursor() as cur:
        cur.execute("delete from milestones where student_id = %s", (student_id,))
        cur.execute("delete from student_ratings where student_id = %s", (student_id,))
        cur.execute("delete from student_objective_status where student_id = %s", (student_id,))
        cur.execute("delete from objectives where id = %s", (objective_id,))
        cur.execute("delete from students where id = %s", (student_id,))
        cur.execute("delete from classes where id = %s", (class_id,))
    conn.close()

if not ok:
    sys.exit("\nOne or more RLS checks failed.")

print("\nAll RLS checks passed.")
