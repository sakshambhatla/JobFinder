-- External job board cache (YC Jobs API, future RapidAPI sources).
-- One row per (user, source) — upserted on each fetch.

create table if not exists public.external_job_cache (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  source      text not null,
  cached_at   timestamptz not null default now(),
  expires_at  timestamptz not null,
  total_jobs  int not null default 0,
  jobs        jsonb not null default '[]'::jsonb,
  created_at  timestamptz not null default now(),
  constraint  uq_ext_cache_user_source unique (user_id, source)
);

-- RLS
alter table public.external_job_cache enable row level security;

create policy "Users can read own cache"
  on public.external_job_cache for select
  using (auth.uid() = user_id);

create policy "Users can insert own cache"
  on public.external_job_cache for insert
  with check (auth.uid() = user_id);

create policy "Users can update own cache"
  on public.external_job_cache for update
  using (auth.uid() = user_id);

create policy "Users can delete own cache"
  on public.external_job_cache for delete
  using (auth.uid() = user_id);
