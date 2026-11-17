/**
 * Shared Sentry runtime options for client / server / edge init.
 * DSN comes from NEXT_PUBLIC_SENTRY_DSN (public by design).
 */

export function getSentryDsn(): string | undefined {
  const dsn = (process.env.NEXT_PUBLIC_SENTRY_DSN || "").trim();
  return dsn || undefined;
}

export function getSentryEnvironment(): string | undefined {
  const env = (
    process.env.SENTRY_ENVIRONMENT ||
    process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ||
    process.env.VERCEL_ENV ||
    process.env.NODE_ENV ||
    ""
  ).trim();
  return env || undefined;
}

/** 100% in development, 10% in production by default. */
export function getTracesSampleRate(): number {
  const raw = process.env.SENTRY_TRACES_SAMPLE_RATE;
  if (raw != null && raw.trim() !== "") {
    const parsed = Number(raw);
    if (Number.isFinite(parsed)) {
      return Math.min(1, Math.max(0, parsed));
    }
  }
  return process.env.NODE_ENV === "development" ? 1.0 : 0.1;
}
