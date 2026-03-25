-- Offer analyses: LLM-powered company evaluation for offer-stage entries

create table if not exists public.offer_analyses (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  company_name    text not null,
  personal_context text not null default '',
  dimensions      jsonb not null default '[]',
  weighted_score  numeric(4,2),
  raw_average     numeric(4,2),
  verdict         text,
  key_question    text,
  flags           jsonb not null default '{"red":0,"yellow":0,"green":0}',
  model_provider  text,
  model_name      text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create unique index if not exists idx_offer_analyses_user_company
  on public.offer_analyses (user_id, lower(company_name));

alter table public.offer_analyses enable row level security;

create policy "Users can manage own offer analyses"
  on public.offer_analyses for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
