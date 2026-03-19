-- ── API Profiles: audit trail columns + trigger ───────────────────────────────
-- Adds created_by / updated_by / updated_at to the shared api_profiles table
-- so every write is traceable to a specific authenticated user.
-- A BEFORE trigger enforces the audit columns at the database level (unforgeable).

-- 1. Add audit columns (nullable for pre-existing rows)
alter table public.api_profiles
  add column if not exists created_by  uuid references auth.users(id),
  add column if not exists updated_by  uuid references auth.users(id),
  add column if not exists updated_at  timestamptz not null default now();

-- 2. Trigger: auto-set audit columns on INSERT / UPDATE
create or replace function public.set_api_profile_audit()
returns trigger as $$
begin
  if tg_op = 'INSERT' then
    new.created_by := auth.uid();
    new.updated_by := auth.uid();
    new.updated_at := now();
  elsif tg_op = 'UPDATE' then
    new.created_by := old.created_by;   -- preserve original creator
    new.updated_by := auth.uid();
    new.updated_at := now();
  end if;
  return new;
end;
$$ language plpgsql;

create trigger api_profiles_audit_trigger
  before insert or update on public.api_profiles
  for each row execute function public.set_api_profile_audit();

-- 3. Recreate RLS policies (same auth level; trigger enforces audit trail)
drop policy if exists "Authenticated users can insert API profiles" on public.api_profiles;
drop policy if exists "Authenticated users can update API profiles" on public.api_profiles;

create policy "Authenticated users can insert API profiles"
  on public.api_profiles for insert
  with check (auth.role() = 'authenticated');

create policy "Authenticated users can update API profiles"
  on public.api_profiles for update
  using (auth.role() = 'authenticated');
