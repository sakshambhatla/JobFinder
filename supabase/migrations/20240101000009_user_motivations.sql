-- User motivations: stores the chat conversation + LLM-generated summary
-- that augments resume context during company discovery.

create table if not exists public.user_motivations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  resume_id   text,
  chat_history jsonb not null default '[]'::jsonb,
  summary     text not null default '',
  status      text not null default 'in_progress',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint  uq_motivations_user unique (user_id)
);

alter table public.user_motivations enable row level security;

create policy "Users can read own motivations"
  on public.user_motivations for select
  using (auth.uid() = user_id);

create policy "Users can insert own motivations"
  on public.user_motivations for insert
  with check (auth.uid() = user_id);

create policy "Users can update own motivations"
  on public.user_motivations for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can delete own motivations"
  on public.user_motivations for delete
  using (auth.uid() = user_id);

create index if not exists idx_user_motivations_user_id
  on public.user_motivations(user_id);
