import type { NextConfig } from "next";

const apiProxy =
  process.env.API_PROXY_TARGET?.trim() || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/",
        destination: "/parlament/de_bundestag",
        permanent: false,
      },
      {
        source: "/deutschland/bund",
        destination: "/parlament/de_bundestag",
        permanent: true,
      },
      {
        source: "/szenario",
        destination: "/parlament/de_bundestag",
        permanent: false,
      },
      {
        source: "/parlament/:id/sitze",
        destination: "/parlament/:id",
        permanent: false,
      },
      {
        source: "/parlament/:id/koalitionen",
        destination: "/parlament/:id",
        permanent: false,
      },
      {
        source: "/parlament/:id/institute",
        destination: "/parlament/:id",
        permanent: false,
      },
      {
        source: "/parlament/:id/szenario",
        destination: "/parlament/:id",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    // Lokal: Next proxied /api/* und /health an FastAPI.
    // Auf Vercel (gleiches Projekt) antwortet die Python-Function direkt.
    if (process.env.VERCEL) {
      return [];
    }
    return [
      { source: "/api/:path*", destination: `${apiProxy}/api/:path*` },
      { source: "/health", destination: `${apiProxy}/health` },
    ];
  },
};

export default nextConfig;
