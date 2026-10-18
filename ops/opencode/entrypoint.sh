#!/bin/sh
# Entrypoint for the OpenCode sidecar. When OPENCODE_EGRESS_URL is set, writes
# an extra config file (loaded via OPENCODE_CONFIG) that points the built-in
# `opencode` provider at the Cloudflare Worker egress (ops/egress-worker), so
# OpenCode API traffic exits from Cloudflare IPs instead of this host's.
# /tmp is a tmpfs mount (the root filesystem is read-only), and the real
# OpenCode credential never leaves the container — the worker only sees it in
# the Authorization header it forwards over TLS.
set -eu

if [ -n "${OPENCODE_EGRESS_URL:-}" ]; then
  cat > /tmp/opencode-egress.json <<EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "provider": {
    "opencode": {
      "options": {
        "baseURL": "${OPENCODE_EGRESS_URL}",
        "headers": { "X-Egress-Token": "${OPENCODE_EGRESS_TOKEN:-}" }
      }
    }
  }
}
EOF
  export OPENCODE_CONFIG=/tmp/opencode-egress.json
fi

exec opencode serve --hostname 0.0.0.0 --port 4096
