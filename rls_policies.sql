-- ============================================================
-- Row Level Security for the ESL progress dashboard
--
-- Model:
--   - "authenticated" = teacher accounts via Supabase Auth: admins
--     write, viewers read (see the policy block below).
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

-- Authenticated users split into two roles (see fable-dashboard's
-- migrate_viewer_role.sql, which owns this model):
--   - admins (rows in admin_users, checked via is_admin()): full CRUD
--   - viewers (any other Supabase Auth account): read-only
--
-- This file previously created a blanket "teacher full access" policy for
-- every authenticated user. Because permissive policies are OR'd, re-running
-- it silently gave viewers write access again. It now mirrors the viewer
-- model instead, and drops the blanket policy if present.

do $$
declare t text;
begin
  foreach t in array array[
    'classes', 'students', 'objectives',
    'student_objective_status', 'student_ratings', 'milestones'
  ] loop
    execute format('drop policy if exists "teacher full access" on %I', t);
    execute format('drop policy if exists "authenticated read access" on %I', t);
    execute format(
      'create policy "authenticated read access" on %I
         for select to authenticated using (true)', t);
    execute format('drop policy if exists "admin write access" on %I', t);
    execute format(
      'create policy "admin write access" on %I
         for all to authenticated
         using (public.is_admin()) with check (public.is_admin())', t);
  end loop;
end $$;

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

-- CANONICAL COPY LIVES IN fable-dashboard/rls_policies.sql. This copy is kept
-- identical so that re-running either repo's script never strips a key the
-- other app needs. Edit there, then sync here.
create or replace function public.get_student_portal(p_access_token text)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_student_id uuid;
  v_result json;
begin
  select s.id into v_student_id
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
        'class_level', c.level,
        -- fable-dashboard renders this as the hero headshot; dropping it
        -- silently removes photos for every student who has one.
        'photo_b64', s.photo_b64
      )
      from students s
      left join classes c on c.id = s.class_id
      where s.id = v_student_id
    ),
    -- NOTE: two apps read this function -- progress-dashboard (the six
    -- communication criteria) and fable-dashboard (the original nine). It
    -- therefore returns BOTH sets plus 'objectives', so neither breaks.
    -- Do not trim this payload without checking both consumers.
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
      where o.class_id = (select class_id from students where id = v_student_id)
    ),
    'ratings', (
      select coalesce(json_agg(json_build_object(
        'rating_date', r.rating_date,
        -- six communication criteria (progress-dashboard)
        'fluency_rating', r.fluency_rating,
        'clarity_volume_rating', r.clarity_volume_rating,
        'confidence_willingness_rating', r.confidence_willingness_rating,
        'interactive_engagement_rating', r.interactive_engagement_rating,
        'vocabulary_application_rating', r.vocabulary_application_rating,
        'sentence_construction_rating', r.sentence_construction_rating,
        -- original nine (fable-dashboard)
        'pronunciation_rating', r.pronunciation_rating,
        'confidence_rating', r.confidence_rating,
        'participation_rating', r.participation_rating,
        'listening_rating', r.listening_rating,
        'reading_rating', r.reading_rating,
        'writing_rating', r.writing_rating,
        'grammar_rating', r.grammar_rating,
        'vocabulary_rating', r.vocabulary_rating,
        -- shared
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
    ),
    -- Speaking tests (see migrate_tests.sql), oldest first.
    'tests', (
      select coalesce(json_agg(json_build_object(
        'title', t.title,
        'test_date', t.test_date,
        'communication', tr.communication,
        'fluency', tr.fluency,
        'extension', tr.extension,
        'vocabulary', tr.vocabulary,
        'grammar', tr.grammar,
        'pronunciation', tr.pronunciation,
        'interaction', tr.interaction,
        'multi_sentence', tr.multi_sentence,
        'used_because', tr.used_because,
        'gave_example', tr.gave_example,
        'handled_followup', tr.handled_followup,
        'asked_questions', tr.asked_questions,
        'question_words', tr.question_words,
        'recovery_phrase', tr.recovery_phrase,
        'stayed_in_english', tr.stayed_in_english,
        'comments', tr.comments
      ) order by t.test_date asc, t.created_at asc), '[]'::json)
      from test_results tr
      join tests t on t.id = tr.test_id
      where tr.student_id = v_student_id
    )
  ) into v_result;

  return v_result;
end;
$$;

revoke all on function public.get_student_portal(text) from public;
grant execute on function public.get_student_portal(text) to anon, authenticated;
