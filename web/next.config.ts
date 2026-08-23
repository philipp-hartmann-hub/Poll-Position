import type { NextConfig } from "next";

const apiProxy =
  process.env.API_PROXY_TARGET?.trim() || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
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
