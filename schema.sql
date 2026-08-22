-- Needed for gen_random_uuid() / gen_random_bytes()
create extension if not exists pgcrypto;

create table if not exists classes (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  level text,
  created_at timestamptz default now()
);

create table if not exists students (
  id uuid primary key default gen_random_uuid(),
  class_id uuid references classes(id),
  name text not null,
  parent_contact text,
  access_token text unique not null default encode(gen_random_bytes(16), 'hex'),
  created_at timestamptz default now()
);

create table if not exists objectives (
  id uuid primary key default gen_random_uuid(),
  class_id uuid references classes(id),
  category text,
  title text not null,
  description text,
  order_index int,
  created_at timestamptz default now()
);

create table if not exists student_objective_status (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id),
  objective_id uuid references objectives(id),
  status text check (status in ('not_started','in_progress','mastered')) default 'not_started',
  notes text,
  updated_at timestamptz default now(),
  unique(student_id, objective_id)
);

create table if not exists student_ratings (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id),
  rating_date date not null default current_date,
  -- The six in-class communication criteria.
  fluency_rating int check (fluency_rating between 1 and 5),
  clarity_volume_rating int check (clarity_volume_rating between 1 and 5),
  confidence_willingness_rating int check (confidence_willingness_rating between 1 and 5),
  interactive_engagement_rating int check (interactive_engagement_rating between 1 and 5),
  vocabulary_application_rating int check (vocabulary_application_rating between 1 and 5),
  sentence_construction_rating int check (sentence_construction_rating between 1 and 5),
  -- Graded and shown to parents, but kept outside the six: it measures work
  -- done at home, not in-class communication.
  homework_rating int check (homework_rating between 1 and 5),
  notes text,
  created_at timestamptz default now()
);

-- One check-in per student per day; the app edits in place rather than
-- inserting a second row.
create unique index if not exists student_ratings_one_per_day
  on student_ratings (student_id, rating_date);

create table if not exists milestones (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id),
  title text not null,
  achieved_at date not null default current_date,
  created_at timestamptz default now()
);
