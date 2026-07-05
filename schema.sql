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
  pronunciation_rating text check (pronunciation_rating in ('needs_work','developing','strong')),
  confidence_rating text check (confidence_rating in ('needs_work','developing','strong')),
  notes text,
  created_at timestamptz default now()
);

create table if not exists milestones (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id),
  title text not null,
  achieved_at date not null default current_date,
  created_at timestamptz default now()
);
