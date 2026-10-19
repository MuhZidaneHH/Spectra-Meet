import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";
import path from "node:path";

// Konfigurasi dibaca dari .env di akar repo, satu file untuk web dan API.
loadEnvConfig(path.resolve(process.cwd(), ".."));

const apiOrigin = `http://127.0.0.1:${process.env.API_PORT || "8000"}`;

// Unggahan audio melewati proxy Next.js. Batas bawaannya 10 MB, jadi file yang lebih besar
// ditolak dengan "Internal Server Error" walau API-nya sendiri menerima. Samakan dengan batas
// unggahan di .env (ditambah sedikit ruang untuk bagian form).
const maxUploadMb = Number(process.env.MAX_UPLOAD_MB) || 200;

const nextConfig: NextConfig = {
  experimental: {
    proxyClientMaxBodySize: `${maxUploadMb + 10}mb`,
  },
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
