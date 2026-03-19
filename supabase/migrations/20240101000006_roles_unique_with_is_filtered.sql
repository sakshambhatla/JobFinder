-- Fix: allow filtered and unfiltered rows to coexist for the same (user_id, url).
-- The old constraint only had (user_id, url), so writing filtered roles would
-- overwrite the unfiltered copy via upsert.

alter table public.roles drop constraint if exists uq_roles_user_url;
alter table public.roles
  add constraint uq_roles_user_url unique (user_id, url, is_filtered);
