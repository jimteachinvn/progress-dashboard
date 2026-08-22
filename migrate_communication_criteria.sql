-- Moves student_ratings onto the six communication criteria this class
-- actually teaches, with Homework quality retained as a standalone measure.
--
-- The old columns (pronunciation/confidence/participation/listening/reading/
-- writing/grammar/vocabulary) are deliberately LEFT IN PLACE as a backup.
-- The app stops reading them; the data stays recoverable.
--
-- Safe to run more than once.

-- 1. New columns -------------------------------------------------------------

alter table student_ratings add column if not exists fluency_rating int
  check (fluency_rating between 1 and 5);
alter table student_ratings add column if not exists clarity_volume_rating int
  check (clarity_volume_rating between 1 and 5);
alter table student_ratings add column if not exists confidence_willingness_rating int
  check (confidence_willingness_rating between 1 and 5);
alter table student_ratings add column if not exists interactive_engagement_rating int
  check (interactive_engagement_rating between 1 and 5);
alter table student_ratings add column if not exists vocabulary_application_rating int
  check (vocabulary_application_rating between 1 and 5);
alter table student_ratings add column if not exists sentence_construction_rating int
  check (sentence_construction_rating between 1 and 5);

-- 2. Carry forward the five mappable criteria --------------------------------
-- Only fills blanks, so re-running never clobbers newly entered grades.
-- fluency_rating has no historical source and stays null by design.

update student_ratings set
  clarity_volume_rating          = coalesce(clarity_volume_rating,          pronunciation_rating),
  confidence_willingness_rating  = coalesce(confidence_willingness_rating,  confidence_rating),
  interactive_engagement_rating  = coalesce(interactive_engagement_rating,  participation_rating),
  vocabulary_application_rating  = coalesce(vocabulary_application_rating,  vocabulary_rating),
  sentence_construction_rating   = coalesce(sentence_construction_rating,   grammar_rating);

-- 3. De-duplicate the July bulk-import artefacts -----------------------------
-- That import ran three times: the middle pass wrote ratings but lost the
-- notes, the third wrote exact copies. For each (student, date) keep the row
-- carrying the longest notes (ties broken by earliest created_at) and drop
-- the rest. No note text is lost.

with ranked as (
  select id,
         row_number() over (
           partition by student_id, rating_date
           order by coalesce(length(notes), 0) desc, created_at asc
         ) as rn
  from student_ratings
)
delete from student_ratings
where id in (select id from ranked where rn > 1);

-- 4. Prevent it happening again ----------------------------------------------
-- One check-in per student per day. The new editor updates in place rather
-- than inserting, so this constraint costs nothing in normal use.

create unique index if not exists student_ratings_one_per_day
  on student_ratings (student_id, rating_date);
