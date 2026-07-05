-- ============================================================
-- Row Level Security for the ESL progress dashboard
--
-- Model:
--   - "authenticated" = you, the teacher, logged in via Supabase
--     Auth email/password. Full read/write on everything.
--   - "anon" = the publishable key used by both your not-yet-built
--     teacher login page (pre-auth) and the parent portal pages.
--     Anon gets NO direct table access at all. The only way anon
--     can read student data is through the get_student_portal()
--     function below, and only if it presents the correct
--     per-student access_token. Knowledge of that token is the
--     "credential" for the parent portal.
-- ============================================================

alter table classes enable row level security;
alter table students enable row level security;
alter table objectives enable row level security;
alter table student_objective_status enable row level security;
alter table student_ratings enable row level security;
alter table milestones enable row level security;

-- Teacher (any logged-in user) gets full CRUD on every table.
-- This is a single-teacher app, so there's no need to scope by user id.

drop policy if exists "teacher full access" on classes;
create policy "teacher full access" on classes
  for all to authenticated using (true) with check (true);

drop policy if exists "teacher full access" on students;
create policy "teacher full access" on students
  for all to authenticated using (true) with check (true);

drop policy if exists "teacher full access" on objectives;
create policy "teacher full access" on objectives
  for all to authenticated using (true) with check (true);

drop policy if exists "teacher full access" on student_objective_status;
create policy "teacher full access" on student_objective_status
  for all to authenticated using (true) with check (true);

drop policy if exists "teacher full access" on student_ratings;
create policy "teacher full access" on student_ratings
  for all to authenticated using (true) with check (true);

drop policy if exists "teacher full access" on milestones;
create policy "teacher full access" on milestones
  for all to authenticated using (true) with check (true);

-- Defense in depth: Supabase grants anon table-level privileges by default
-- on new tables. We rely entirely on RLS (no anon policy = no rows), but
-- revoke the grants too so a future RLS misconfiguration can't expose data.

revoke all on classes, students, objectives, student_objective_status,
  student_ratings, milestones from anon;

-- ============================================================
-- Parent portal read access, via one token-gated RPC function.
--
-- security definer means this function runs with the privileges of
-- its owner (bypassing RLS internally), but it only ever looks up
-- and returns data for the single student matching the token that
-- was passed in as an argument -- never anything else.
-- ============================================================

create or replace function public.get_student_portal(p_access_token text)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_student_id uuid;
  v_class_id uuid;
  v_result json;
begin
  select s.id, s.class_id into v_student_id, v_class_id
  from students s
  where s.access_token = p_access_token;

  if v_student_id is null then
    return null;
  end if;

  select json_build_object(
    'student', (
      select json_build_object(
        'id', s.id,
        'name', s.name,
        'class_name', c.name,
        'class_level', c.level
      )
      from students s
      left join classes c on c.id = s.class_id
      where s.id = v_student_id
    ),
    'objectives', (
      select coalesce(json_agg(json_build_object(
        'id', o.id,
        'category', o.category,
        'title', o.title,
        'description', o.description,
        'status', coalesce(sos.status, 'not_started'),
        'notes', sos.notes,
        'updated_at', sos.updated_at
      ) order by o.order_index), '[]'::json)
      from objectives o
      left join student_objective_status sos
        on sos.objective_id = o.id and sos.student_id = v_student_id
      where o.class_id = v_class_id
    ),
    'ratings', (
      select coalesce(json_agg(json_build_object(
        'rating_date', r.rating_date,
        'pronunciation_rating', r.pronunciation_rating,
        'confidence_rating', r.confidence_rating,
        'participation_rating', r.participation_rating,
        'homework_rating', r.homework_rating,
        'notes', r.notes
      ) order by r.rating_date asc), '[]'::json)
      from student_ratings r
      where r.student_id = v_student_id
    ),
    'milestones', (
      select coalesce(json_agg(json_build_object(
        'title', m.title,
        'achieved_at', m.achieved_at
      ) order by m.achieved_at desc), '[]'::json)
      from milestones m
      where m.student_id = v_student_id
    )
  ) into v_result;

  return v_result;
end;
$$;

revoke all on function public.get_student_portal(text) from public;
grant execute on function public.get_student_portal(text) to anon, authenticated;
