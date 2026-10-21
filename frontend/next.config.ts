import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

import { resolveBackendUrl } from "./src/constants/api";
import { buildContentSecurityPolicy } from "./src/constants/csp";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const DASHBOARD_PREFIX = "/dashboard";

/** Pre-dashboard URLs that now live under /dashboard (temporary redirects). */
const LEGACY_DASHBOARD_PATHS = [
  "/create",
  "/create/:id",
  "/create/:id/publish",
  "/knowledge",
  "/personas",
  "/rubrics",
  "/blog-posts",
  "/blog-posts/:id/edit",
  "/workflow",
  "/calendar",
  "/analytics",
] as const;

/**
 * Standalone output is opt-in via NEXT_STANDALONE (Docker image). The
 * Content-Security-Policy header comes from src/constants/csp.ts, its single
 * authoritative, env-gated definition (drift-guarded by csp.test.ts).
 */
const nextConfig: NextConfig = {
  output: process.env.NEXT_STANDALONE === "true" ? "standalone" : undefined,

  reactCompiler: true,

  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },

  experimental: {
    optimizePackageImports: ["lucide-react", "@radix-ui/react-icons"],
  },

  compress: true,

  poweredByHeader: false,

  trailingSlash: false,

  rewrites() {
    const backendUrl = resolveBackendUrl();
    return Promise.resolve([
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/ws/:path*",
        destination: `${backendUrl}/ws/:path*`,
      },
    ]);
  },

  redirects() {
    return Promise.resolve([
      { source: "/home", destination: "/", permanent: true },
      ...LEGACY_DASHBOARD_PATHS.map((source) => ({
        source,
        destination: `${DASHBOARD_PREFIX}${source}`,
        permanent: false,
      })),
    ]);
  },

  headers() {
    return Promise.resolve([
      {
        source: "/:path*",
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "origin-when-cross-origin",
          },
          {
            key: "Content-Security-Policy",
            value: buildContentSecurityPolicy(
              process.env.NODE_ENV === "production",
            ),
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
        ],
      },
      {
        source: "/(.*)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=3600, must-revalidate",
          },
        ],
      },
    ]);
  },
};

export default withNextIntl(nextConfig);
