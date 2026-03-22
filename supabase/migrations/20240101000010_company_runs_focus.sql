-- Add focus column to company_runs for startup-targeted discovery
ALTER TABLE public.company_runs ADD COLUMN IF NOT EXISTS focus text DEFAULT NULL;

-- No RLS changes needed: existing policies already cover all columns
