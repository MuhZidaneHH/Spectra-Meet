import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";
import path from "node:path";

// Konfigurasi dibaca dari .env di akar repo, satu file untuk web dan API.
loadEnvConfig(path.resolve(process.cwd(), ".."));

const apiOrigin = `http://127.0.0.1:${process.env.API_PORT || "8000"}`;

const nextConfig: NextConfig = {
  // Browser hanya bicara ke satu alamat (web). Semua /api/* diteruskan ke FastAPI.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
