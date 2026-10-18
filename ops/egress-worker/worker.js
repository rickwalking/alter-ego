// Cloudflare Worker egress for the OpenCode sidecar (ops/opencode).
//
// The sidecar points its `opencode` provider baseURL at this worker, so
// OpenCode API traffic exits from Cloudflare IPs instead of the droplet's.
// The worker is a locked-down reverse proxy: it only forwards to the
// OpenCode inference API, only GET/POST, only allowlisted headers — inbound
// `cf-*` / `x-forwarded-*` headers are dropped so the client's real IP never
// reaches the upstream. Callers authenticate with a shared token
// (`X-Egress-Token`, set via `wrangler secret put EGRESS_TOKEN`); the real
// OpenCode credential stays in the sidecar's auth.json and passes through in
// the Authorization header untouched.

const DEFAULT_UPSTREAM_BASE = "https://opencode.ai/inference/openai/v1";

const ALLOWED_METHODS = new Set(["GET", "POST"]);

const TOKEN_HEADER = "x-egress-token";

const HEADER_ALLOWLIST = new Set([
  "authorization",
  "content-type",
  "accept",
  "user-agent",
  // Session-affinity hints the opencode client adds to LLM requests.
  // Session UUIDs, no IP.
  "x-session-affinity",
  "x-session-id",
  "x-parent-session-id",
]);

// `x-opencode-` carries the opencode client markers (session id, parent
// session id) — a session UUID, no IP. Without them the upstream rejects
// free-tier models with FreeTierError.
const HEADER_PREFIX_ALLOWLIST = [
  "x-stainless-",
  "openai-",
  "ai-sdk",
  "x-opencode-",
];

function isAllowedHeader(name) {
  const lower = name.toLowerCase();
  if (HEADER_ALLOWLIST.has(lower)) {
    return true;
  }
  return HEADER_PREFIX_ALLOWLIST.some((prefix) => lower.startsWith(prefix));
}

export default {
  async fetch(request, env) {
    if (!ALLOWED_METHODS.has(request.method)) {
      return new Response("method not allowed", { status: 405 });
    }
    if (!env.EGRESS_TOKEN || request.headers.get(TOKEN_HEADER) !== env.EGRESS_TOKEN) {
      return new Response("unauthorized", { status: 401 });
    }
    const url = new URL(request.url);
    const headers = new Headers();
    for (const [name, value] of request.headers) {
      if (isAllowedHeader(name)) {
        headers.set(name, value);
      }
    }
    const upstreamBase = env.UPSTREAM_BASE || DEFAULT_UPSTREAM_BASE;
    const upstream = new Request(upstreamBase + url.pathname + url.search, {
      method: request.method,
      headers,
      body: request.method === "GET" ? null : request.body,
      // Required by runtimes that stream request bodies (ignored where N/A).
      duplex: "half",
      redirect: "manual",
    });
    return fetch(upstream);
  },
};
