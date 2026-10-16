// Menjalankan Next.js dengan konfigurasi dari .env di AKAR repo (bukan folder web).
// Dipakai oleh `npm run dev`, `npm start`, dan skrip akar (scripts/spectrameet.mjs).
//   node scripts/run-next.mjs dev     server pengembangan (port dari WEB_PORT)
//   node scripts/run-next.mjs build   build produksi
//   node scripts/run-next.mjs start   server produksi (port dari WEB_PORT)
import nextEnv from "@next/env";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const mode = ["start", "build"].includes(process.argv[2]) ? process.argv[2] : "dev";

nextEnv.loadEnvConfig(repoRoot, mode === "dev");

const nextBin = createRequire(import.meta.url).resolve("next/dist/bin/next");
const port = process.env.WEB_PORT || "3000";
const args = mode === "build" ? [nextBin, "build"] : [nextBin, mode, "-p", port];

const child = spawn(process.execPath, args, {
  stdio: "inherit",
  env: process.env,
});
child.on("exit", (code) => process.exit(code ?? 0));
