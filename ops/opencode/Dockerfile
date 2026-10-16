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

# AE-0402: OpenCode writes into its install dir and the whole home at runtime
# (.opencode/.gitignore, plugin npm installs, cache, state). The root stays
# read-only, so the binary moves out of home and compose mounts /home/opencode
# as a tmpfs (owned by 10001), with only the opencode_data volume inside it.
# Its data (login, sessions, logs) lives on the opencode_data volume at
# /data/opencode, outside the tmpfs home: a mount nested in the tmpfs would get
# root-owned parent directories.
USER root
RUN install -m 0755 /home/opencode/.opencode/bin/opencode /usr/local/bin/opencode \
    && rm -rf /home/opencode/.opencode \
    && install -d -o opencode -g opencode -m 0700 /data/opencode
USER opencode

ENV OPENCODE_DISABLE_AUTOUPDATE=true \
    XDG_DATA_HOME=/data

# The agent's only working directory: a tmpfs mount in compose.
WORKDIR /work

EXPOSE 4096
CMD ["opencode", "serve", "--hostname", "0.0.0.0", "--port", "4096"]
