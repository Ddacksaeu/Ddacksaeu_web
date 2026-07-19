import type { NextConfig } from "next";

const backendApiOrigin = (
  process.env["BACKEND_API_ORIGIN"] ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend-api/:path*",
        destination: `${backendApiOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
