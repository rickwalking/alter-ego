# OpenCode sidecar for the carousel model queue (AE-0399).
#
# OpenCode's free models only answer requests made from within OpenCode, and
# OpenCode is a coding agent with shell and file tools. It therefore runs here,
# alone: no secrets in its environment besides its own server password, no
# published ports, a read-only root filesystem (see docker-compose.prod.yml),
# and a throwaway working directory. The backend talks to `opencode serve`
# over the compose network with HTTP Basic auth.
FROM debian:bookworm-slim

ARG OPENCODE_VERSION=1.18.35

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 opencode

USER opencode
WORKDIR /home/opencode
RUN curl -fsSL https://opencode.ai/install | bash -s -- --version "${OPENCODE_VERSION}"

ENV PATH="/home/opencode/.opencode/bin:${PATH}" \
    OPENCODE_DISABLE_AUTOUPDATE=true

# The agent's only working directory: a tmpfs mount in compose.
WORKDIR /work

EXPOSE 4096
CMD ["opencode", "serve", "--hostname", "0.0.0.0", "--port", "4096"]
