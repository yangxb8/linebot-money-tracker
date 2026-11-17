import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  getSentryDsn,
  getSentryEnvironment,
  getTracesSampleRate,
} from "./config";

const KEYS = [
  "NEXT_PUBLIC_SENTRY_DSN",
  "SENTRY_ENVIRONMENT",
  "NEXT_PUBLIC_SENTRY_ENVIRONMENT",
  "VERCEL_ENV",
  "NODE_ENV",
  "SENTRY_TRACES_SAMPLE_RATE",
] as const;

describe("sentry config helpers", () => {
  const originals: Record<string, string | undefined> = {};

  beforeEach(() => {
    for (const key of KEYS) {
      originals[key] = process.env[key];
    }
  });

  afterEach(() => {
    for (const key of KEYS) {
      const value = originals[key];
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  });

  it("returns undefined DSN when unset or blank", () => {
    delete process.env.NEXT_PUBLIC_SENTRY_DSN;
    expect(getSentryDsn()).toBeUndefined();
    process.env.NEXT_PUBLIC_SENTRY_DSN = "   ";
    expect(getSentryDsn()).toBeUndefined();
  });

  it("trims and returns the DSN", () => {
    process.env.NEXT_PUBLIC_SENTRY_DSN =
      " https://key@o1.ingest.sentry.io/2 ";
    expect(getSentryDsn()).toBe("https://key@o1.ingest.sentry.io/2");
  });

  it("resolves environment with fallbacks", () => {
    delete process.env.SENTRY_ENVIRONMENT;
    delete process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT;
    delete process.env.VERCEL_ENV;
    process.env.NODE_ENV = "test";
    expect(getSentryEnvironment()).toBe("test");

    process.env.VERCEL_ENV = "preview";
    expect(getSentryEnvironment()).toBe("preview");

    process.env.SENTRY_ENVIRONMENT = "production";
    expect(getSentryEnvironment()).toBe("production");
  });

  it("clamps traces sample rate and defaults by NODE_ENV", () => {
    delete process.env.SENTRY_TRACES_SAMPLE_RATE;
    process.env.NODE_ENV = "development";
    expect(getTracesSampleRate()).toBe(1.0);
    process.env.NODE_ENV = "production";
    expect(getTracesSampleRate()).toBe(0.1);

    process.env.SENTRY_TRACES_SAMPLE_RATE = "0.25";
    expect(getTracesSampleRate()).toBe(0.25);
    process.env.SENTRY_TRACES_SAMPLE_RATE = "2";
    expect(getTracesSampleRate()).toBe(1);
    process.env.SENTRY_TRACES_SAMPLE_RATE = "-1";
    expect(getTracesSampleRate()).toBe(0);
    process.env.SENTRY_TRACES_SAMPLE_RATE = "nope";
    expect(getTracesSampleRate()).toBe(0.1);
  });
});
