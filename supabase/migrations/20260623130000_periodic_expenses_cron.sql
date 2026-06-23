-- Schedule hourly periodic expense processing via Supabase Edge Function.
-- Requires vault secret `supabase_service_role_key` (see quickstart).

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'process-periodic-expenses-hourly') THEN
    PERFORM cron.unschedule('process-periodic-expenses-hourly');
  END IF;
END $$;

SELECT cron.schedule(
  'process-periodic-expenses-hourly',
  '0 * * * *',
  $$
  SELECT net.http_post(
    url := 'https://nyuenufldaqsjybjhawl.supabase.co/functions/v1/process-periodic-expenses',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'apikey', (
        SELECT decrypted_secret
        FROM vault.decrypted_secrets
        WHERE name = 'supabase_service_role_key'
        LIMIT 1
      )
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 60000
  ) AS request_id;
  $$
);
