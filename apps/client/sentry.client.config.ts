import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
  debug: process.env.NODE_ENV === "development",
  replaysOnErrorSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  ignoreErrors: [
    // Firefox Reader Mode 확장 프로그램
    /window\.__firefox__/,
    /__firefox__/,
    // MetaMask / Web3 지갑 확장 프로그램
    /window\.ethereum/,
  ],
});
