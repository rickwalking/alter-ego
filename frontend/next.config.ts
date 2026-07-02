import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

import { buildContentSecurityPolicy } from "./src/constants/csp";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

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
      process.env.API_BASE_URL ||
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

  // Redirects
  async redirects() {
    return [
      {
        source: "/home",
        destination: "/",
        permanent: true,
      },
      {
        source: "/create",
        destination: "/dashboard/create",
        permanent: false,
      },
      {
        source: "/create/:id",
        destination: "/dashboard/create/:id",
        permanent: false,
      },
      {
        source: "/create/:id/publish",
        destination: "/dashboard/create/:id/publish",
        permanent: false,
      },
      {
        source: "/knowledge",
        destination: "/dashboard/knowledge",
        permanent: false,
      },
      {
        source: "/personas",
        destination: "/dashboard/personas",
        permanent: false,
      },
      {
        source: "/rubrics",
        destination: "/dashboard/rubrics",
        permanent: false,
      },
      {
        source: "/blog-posts",
        destination: "/dashboard/blog-posts",
        permanent: false,
      },
      {
        source: "/blog-posts/:id/edit",
        destination: "/dashboard/blog-posts/:id/edit",
        permanent: false,
      },
      {
        source: "/workflow",
        destination: "/dashboard/workflow",
        permanent: false,
      },
      {
        source: "/calendar",
        destination: "/dashboard/calendar",
        permanent: false,
      },
      {
        source: "/analytics",
        destination: "/dashboard/analytics",
        permanent: false,
      },
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
