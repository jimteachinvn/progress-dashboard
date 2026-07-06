-- Adds the 5 additional skills needed for the parent radar chart and
-- competency gauges: Listening, Reading, Writing, Grammar accuracy, Vocabulary.
-- Same 1-5 star scale as the existing 4 criteria.

alter table student_ratings add column if not exists listening_rating int
  check (listening_rating between 1 and 5);
alter table student_ratings add column if not exists reading_rating int
  check (reading_rating between 1 and 5);
alter table student_ratings add column if not exists writing_rating int
  check (writing_rating between 1 and 5);
alter table student_ratings add column if not exists grammar_rating int
  check (grammar_rating between 1 and 5);
alter table student_ratings add column if not exists vocabulary_rating int
  check (vocabulary_rating between 1 and 5);
