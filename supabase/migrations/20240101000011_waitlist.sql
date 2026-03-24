-- Waitlist table for landing page signups
create table if not exists public.waitlist (
  id         uuid primary key default gen_random_uuid(),
  email      text not null unique,
  created_at timestamptz not null default now()
);

-- No RLS needed — access is via service role key from the backend only.
-- The table is not exposed to anon/authenticated roles.
alter table public.waitlist enable row level security;
