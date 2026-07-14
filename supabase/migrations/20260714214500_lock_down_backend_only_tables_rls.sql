-- Lock down bot-only public tables that had RLS disabled (Supabase lint 0013).
-- These tables are accessed exclusively via the service_role client from the
-- Python bot / scripts; the web dashboard does not query them.
-- Enabling RLS with no anon/authenticated policies blocks PostgREST public
-- access while service_role continues to bypass RLS.

ALTER TABLE public.user_usage_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.llm_usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.llm_message_windows ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.category_merchant_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.category_item_memory ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.user_usage_summary FROM anon, authenticated;
REVOKE ALL ON public.llm_usage_events FROM anon, authenticated;
REVOKE ALL ON public.llm_message_windows FROM anon, authenticated;
REVOKE ALL ON public.category_merchant_memory FROM anon, authenticated;
REVOKE ALL ON public.category_item_memory FROM anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_usage_summary TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.llm_usage_events TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.llm_message_windows TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.category_merchant_memory TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.category_item_memory TO service_role;
