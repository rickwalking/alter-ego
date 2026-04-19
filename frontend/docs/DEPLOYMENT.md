# Deployment Guide

This guide covers deploying the RAG Chat application to various platforms.

## Table of Contents

- [Vercel (Recommended)](#vercel-recommended)
- [Docker](#docker)
- [Static Export](#static-export)
- [Environment Variables](#environment-variables)
- [Post-Deployment Checklist](#post-deployment-checklist)

## Vercel (Recommended)

Vercel is the easiest way to deploy Next.js applications with zero configuration.

### Using Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel

# Deploy to production
vercel --prod
```

### Using Git Integration

1. Push your code to GitHub/GitLab/Bitbucket
2. Import your repository on [Vercel Dashboard](https://vercel.com/dashboard)
3. Vercel will automatically detect Next.js and configure build settings
4. Add environment variables in the dashboard
5. Deploy!

### Vercel Configuration

Create `vercel.json` for custom configuration:

```json
{
  "regions": ["iad1"],
  "functions": {
    "app/api/**/*.ts": {
      "maxDuration": 30
    }
  }
}
```

## Docker

### Build Docker Image

```dockerfile
# Dockerfile
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED 1
ENV NODE_ENV production

RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverage output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

### Build and Run

```bash
# Build image
docker build -t rag-chat .

# Run container
docker run -p 3000:3000 rag-chat

# With environment variables
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=https://api.example.com \
  rag-chat
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NODE_ENV=production
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## Static Export

For hosting on static site generators (Netlify, GitHub Pages, etc.):

```javascript
// next.config.ts
const nextConfig = {
  output: 'export',
  distDir: 'dist',
}
```

```bash
npm run build
# Output will be in 'dist' folder
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `https://api.example.com` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_ENV` | Environment mode | `development` |
| `NEXT_TELEMETRY_DISABLED` | Disable Next.js telemetry | `0` |

### Production Checklist

- [ ] Set `NODE_ENV=production`
- [ ] Configure `NEXT_PUBLIC_API_URL`
- [ ] Enable analytics (Vercel Analytics)
- [ ] Set up monitoring (Sentry, LogRocket)
- [ ] Configure custom domain
- [ ] Enable HTTPS
- [ ] Set up CI/CD pipeline
- [ ] Configure caching headers
- [ ] Test error boundaries
- [ ] Verify SEO meta tags

## Platform-Specific Guides

### Netlify

```toml
# netlify.toml
[build]
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"
```

### AWS Amplify

1. Connect your repository in AWS Amplify Console
2. Build settings will be auto-detected
3. Add environment variables in the console
4. Deploy

### Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

## Troubleshooting

### Build Failures

1. Check Node.js version (requires 18+)
2. Clear `.next` folder and `node_modules`
3. Run `npm ci` instead of `npm install`

### Runtime Errors

1. Verify environment variables are set
2. Check API connectivity
3. Review server logs

### Performance Issues

1. Enable React Compiler
2. Check bundle size with `@next/bundle-analyzer`
3. Optimize images
4. Use CDN for static assets

## Support

For deployment issues:
- [Next.js Deployment Docs](https://nextjs.org/docs/deployment)
- [Vercel Docs](https://vercel.com/docs)
- [Docker Docs](https://docs.docker.com/)
