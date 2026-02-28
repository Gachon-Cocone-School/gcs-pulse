import path from 'node:path';
import { fileURLToPath } from 'node:url';

/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const monorepoRoot = path.resolve(__dirname, '../..');

const connectSrcOrigins = new Set(["'self'", 'https:']);

if (isDev) {
  connectSrcOrigins.add('ws:');
  connectSrcOrigins.add('wss:');
  connectSrcOrigins.add('http:');
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL;
if (apiUrl) {
  try {
    connectSrcOrigins.add(new URL(apiUrl).origin);
  } catch {
    // ignore invalid URL
  }
}

const csp = [
  "default-src 'self'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  "object-src 'none'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  isDev
    ? "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: http:"
    : "script-src 'self' 'unsafe-inline'",
  `connect-src ${Array.from(connectSrcOrigins).join(' ')}`,
].join('; ');

const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: csp,
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY',
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff',
  },
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin',
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=()'
  }
];

const nextConfig = {
  turbopack: {
    root: monorepoRoot,
  },
  outputFileTracingRoot: monorepoRoot,
  allowedDevOrigins: ['app-dev.1000.school'],
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
