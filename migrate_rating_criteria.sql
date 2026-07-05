-- Moves student_ratings from 3-level text ratings to a 5-star (1-5) scale,
-- and adds participation_rating / homework_rating alongside the existing
-- pronunciation_rating / confidence_rating.

alter table student_ratings drop constraint if exists student_ratings_pronunciation_rating_check;
alter table student_ratings drop constraint if exists student_ratings_confidence_rating_check;

alter table student_ratings
  alter column pronunciation_rating type int using (
    case pronunciation_rating
      when 'needs_work' then 1
      when 'developing' then 3
      when 'strong' then 5
      else null
    end
  );

alter table student_ratings
  alter column confidence_rating type int using (
    case confidence_rating
      when 'needs_work' then 1
      when 'developing' then 3
      when 'strong' then 5
      else null
    end
  );

alter table student_ratings add column if not exists participation_rating int;
alter table student_ratings add column if not exists homework_rating int;

alter table student_ratings add constraint student_ratings_pronunciation_rating_check
  check (pronunciation_rating between 1 and 5);
alter table student_ratings add constraint student_ratings_confidence_rating_check
  check (confidence_rating between 1 and 5);
alter table student_ratings add constraint student_ratings_participation_rating_check
  check (participation_rating between 1 and 5);
alter table student_ratings add constraint student_ratings_homework_rating_check
  check (homework_rating between 1 and 5);
