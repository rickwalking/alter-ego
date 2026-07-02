/**
 * Content-Security-Policy — the SINGLE authoritative definition (AE-0305).
 *
 * next.config.ts consumes `buildContentSecurityPolicy`; nginx sets no CSP and
 * must stay silent (guarded by csp.test.ts). The `http://localhost:8000`
 * img-src entry exists only so `next dev` can render images served by the
 * local backend — it is a development artifact and never ships to production.
 *
 * Scope note (ticket AE-0305): the `img-src https:` wildcard is deliberately
 * unchanged — tightening it is a separate decision, out of scope here.
 */

export const CSP_DEV_BACKEND_IMG_SOURCE = "http://localhost:8000";

const CSP_IMG_SRC_BASE = "img-src 'self' data: blob: https:";

const CSP_DIRECTIVES_BEFORE_IMG: readonly string[] = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://va.vercel-scripts.com https://static.cloudflareinsights.com",
  "style-src 'self' 'unsafe-inline'",
];

const CSP_DIRECTIVES_AFTER_IMG: readonly string[] = [
  "font-src 'self'",
  "connect-src 'self' ws: wss: http: https:",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
];

export function buildContentSecurityPolicy(isProduction: boolean): string {
  const imgSrc = isProduction
    ? CSP_IMG_SRC_BASE
    : `${CSP_IMG_SRC_BASE} ${CSP_DEV_BACKEND_IMG_SOURCE}`;
  const directives = [
    ...CSP_DIRECTIVES_BEFORE_IMG,
    imgSrc,
    ...CSP_DIRECTIVES_AFTER_IMG,
  ];
  return `${directives.join("; ")};`;
}
