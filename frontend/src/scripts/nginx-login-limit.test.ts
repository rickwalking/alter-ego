/**
 * nginx rate-limits the no-JavaScript sign-in (`POST /auth/login`, served by
 * Next.js) per client IP: the backend's own login limit only sees the frontend
 * container's address. Checks both server configs; fires on a seeded config
 * whose /auth/login location has no limit.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const NGINX_DIR = join(import.meta.dirname, "..", "..", "..", "nginx");
const CONFIGS = ["nginx.conf", "nginx.conf.ssl"];
const LOGIN_LOCATION = "location = /auth/login {";
const BLOCK_END = "}";
const LIMIT_REQ_PREFIX = "limit_req zone=";
const FRONTEND_PROXY = "proxy_pass http://frontend;";

/** Whether the config has an exact /auth/login location that is rate-limited and proxied to Next.js. */
function limitsLogin(config: string): boolean {
  const start = config.indexOf(LOGIN_LOCATION);
  if (start < 0) return false;
  const bodyStart = start + LOGIN_LOCATION.length;
  const lines = config
    .slice(bodyStart, config.indexOf(BLOCK_END, bodyStart))
    .split("\n")
    .map((line) => line.trim());
  return (
    lines.some((line) => line.startsWith(LIMIT_REQ_PREFIX)) &&
    lines.includes(FRONTEND_PROXY)
  );
}

describe("nginx /auth/login limit", () => {
  // Scenario: The no-JavaScript sign-in is rate-limited per client
  it.each(CONFIGS)("%s rate-limits /auth/login", (name) => {
    expect(limitsLogin(readFileSync(join(NGINX_DIR, name), "utf8"))).toBe(true);
  });

  // Scenario: The no-JavaScript sign-in is rate-limited per client
  it.each([
    ["location / {\n  proxy_pass http://frontend;\n}"],
    ["location = /auth/login {\n  proxy_pass http://frontend;\n}"],
    [
      "location = /auth/login {\n  # limit_req zone=api burst=5;\n  proxy_pass http://frontend;\n}",
    ],
  ])("fires on a seeded config without the limit: %j", (config) => {
    expect(limitsLogin(config)).toBe(false);
  });
});
