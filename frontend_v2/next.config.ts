import type { NextConfig } from "next";

const backendApiOrigin = (
  process.env["BACKEND_API_ORIGIN"] ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");
const showcaseMode = process.env["NEXT_PUBLIC_DEPLOYMENT_MODE"] === "showcase";

const nextConfig: NextConfig = {
  async rewrites() {
    if (showcaseMode) return [];
    return [
      {
        source: "/backend-api/:path*",
        destination: `${backendApiOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
