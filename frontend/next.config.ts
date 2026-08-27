import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Local next dev proxies /api to uvicorn. On Vercel, vercel.json routes
    // /api/* to the backend service — never rewrite to localhost there.
    if (process.env.VERCEL) {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
