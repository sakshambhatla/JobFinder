-- Page view analytics.
-- Tracks visits across all routes (public + authenticated).
-- No RLS policies — all access via service role key from the backend
-- (same pattern as the waitlist table).

CREATE TABLE public.page_views (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  session_id    text NOT NULL,
  page_path     text NOT NULL,
  referrer      text,
  user_agent    text,
  screen_width  int,
  screen_height int,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_page_views_created_at ON public.page_views (created_at DESC);
CREATE INDEX idx_page_views_page_path  ON public.page_views (page_path, created_at DESC);
CREATE INDEX idx_page_views_user_id    ON public.page_views (user_id, created_at DESC);

ALTER TABLE public.page_views ENABLE ROW LEVEL SECURITY;
