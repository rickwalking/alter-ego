import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

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

const nextConfig: NextConfig = {
  // Standalone output for Docker (reduces image size)
  output: process.env.NEXT_STANDALONE === "true" ? "standalone" : undefined,

  // Enable React Compiler for automatic memoization
  reactCompiler: true,

  // Image optimization
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },

  // Experimental features for performance
  experimental: {
    // Optimize package imports for faster builds
    optimizePackageImports: ["lucide-react", "@radix-ui/react-icons"],
  },

  // Compression
  compress: true,

  // Powered by header
  poweredByHeader: false,

  // Trailing slash for SEO
  trailingSlash: false,

  // Rewrites to proxy API requests to backend (Docker/Dev)
  async rewrites() {
    const backendUrl =
      process.env.API_BASE_URL ??
      (process.env.NODE_ENV === "production"
        ? "http://backend:8000"
        : "http://localhost:8000");
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/ws/:path*",
        destination: `${backendUrl}/ws/:path*`,
      },
    ];
  },

  // Redirects: /home -> /, and the pre-dashboard paths -> /dashboard/*.
  async redirects() {
    return [
      { source: "/home", destination: "/", permanent: true },
      ...LEGACY_DASHBOARD_PATHS.map((source) => ({
        source,
        destination: `${DASHBOARD_PREFIX}${source}`,
        permanent: false,
      })),
    ];
  },

  // Headers for security and performance
  async headers() {
    return [
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
            // AE-0305: single authoritative CSP definition lives in
            // src/constants/csp.ts (env-gated; drift-guarded by csp.test.ts).
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
    ];
  },
};

export default withNextIntl(nextConfig);
