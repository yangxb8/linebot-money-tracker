import * as Sentry from "@sentry/nextjs";
import {
  getSentryDsn,
  getSentryEnvironment,
  getTracesSampleRate,
} from "@/lib/sentry/config";

const dsn = getSentryDsn();

Sentry.init({
  dsn,
  enabled: Boolean(dsn),
  environment: getSentryEnvironment(),
  tracesSampleRate: getTracesSampleRate(),
  integrations: [
    Sentry.consoleLoggingIntegration({
      levels: ["warn", "error"],
    }),
  ],
});
