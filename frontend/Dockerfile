# syntax=docker/dockerfile:1
FROM node:22-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
# BuildKit cache mount (AE-0192): persists the npm cache across builds so
# repeated `npm ci` runs (e.g. droplet rebuilds) skip re-downloading packages.
RUN --mount=type=cache,target=/root/.npm npm ci --ignore-scripts

FROM node:22-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL
ENV NODE_ENV=production
ENV NEXT_STANDALONE=true
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
# AE-0390: bind every IPv4 interface. Docker sets HOSTNAME to the container id
# and the standalone server listens on it, so a loopback probe was refused.
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    chown -R nextjs:nodejs /app

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

# AE-0390: probe 127.0.0.1, not localhost. busybox wget resolves localhost to
# [::1] first and Next.js listens on IPv4 only, so the probe was refused (prod
# frontend stuck "unhealthy"). /api/* is proxied to the backend, so the probe
# reads /robots.txt: Next.js serves it itself, with no redirect and no backend.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/robots.txt || exit 1

CMD ["node", "server.js"]
