// Pemasangan dan penjalan SpectraMeet dengan satu perintah (Windows, Linux, macOS).
//   node scripts/spectrameet.mjs setup   membuat .env, venv API, dan paket web (aman diulang)
//   node scripts/spectrameet.mjs dev     API + web, mode pengembangan
//   node scripts/spectrameet.mjs start   build web, lalu API + web, mode server
// Pipeline AI (FFmpeg, WhisperX) tidak dipasang di sini; lihat README bagian Pipeline.

import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const WIN = process.platform === "win32";
const API_DIR = path.join(ROOT, "api");
const WEB_DIR = path.join(ROOT, "web");
const VENV_PY = path.join(API_DIR, ".venv", WIN ? "Scripts/python.exe" : "bin/python");
const NPM = WIN ? "npm.cmd" : "npm";

const log = (msg) => console.log(`\x1b[35m[spectrameet]\x1b[0m ${msg}`);
const die = (msg) => {
  console.error(`\x1b[31m[spectrameet] ${msg}\x1b[0m`);
  process.exit(1);
};

// Terminal yang dibuka sebelum FFmpeg dipasang masih memakai PATH lama. Di Windows, ambil PATH
// terbaru dari registri (pengguna + sistem) agar API dan pipeline tetap menemukan ffmpeg.
function refreshWindowsPath() {
  if (!WIN) return;
  const r = spawnSync(
    "powershell",
    ["-NoProfile", "-Command", "[Environment]::GetEnvironmentVariable('Path','Machine')+';'+[Environment]::GetEnvironmentVariable('Path','User')"],
    { encoding: "utf8" },
  );
  if (r.status !== 0) return;
  const key = Object.keys(process.env).find((k) => k.toLowerCase() === "path") ?? "Path";
  const seen = new Set();
  const merged = [...r.stdout.trim().split(";"), ...(process.env[key] ?? "").split(";")].filter((p) => {
    const k = p.trim().toLowerCase();
    if (!k || seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  process.env[key] = merged.join(";");
}

function readEnv() {
  const env = {};
  const file = path.join(ROOT, ".env");
  if (!fs.existsSync(file)) return env;
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (m && !m[1].startsWith("#")) env[m[1]] = m[2];
  }
  return env;
}

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: "inherit", shell: WIN && cmd.endsWith(".cmd"), ...opts });
  if (r.status !== 0) die(`Perintah gagal: ${cmd} ${args.join(" ")}`);
}

function findPython() {
  const candidates = WIN ? [["py", ["-3"]], ["python", []]] : [["python3", []], ["python", []]];
  for (const [cmd, pre] of candidates) {
    const r = spawnSync(cmd, [...pre, "-c", "import sys;print(sys.version_info[:2]>=(3,10))"], { encoding: "utf8" });
    if (r.status === 0 && r.stdout.trim() === "True") return [cmd, pre];
  }
  return null;
}

function setup() {
  const envFile = path.join(ROOT, ".env");
  if (!fs.existsSync(envFile)) {
    fs.copyFileSync(path.join(ROOT, ".env.example"), envFile);
    log(".env dibuat dari .env.example");
  } else {
    log(".env sudah ada, tidak diubah");
  }

  if (!fs.existsSync(VENV_PY)) {
    const py = findPython();
    if (!py) die("Python 3.10 atau lebih baru tidak ditemukan. Pasang Python dulu (Linux: sudo apt install python3-venv).");
    log("Membuat lingkungan Python untuk API...");
    run(py[0], [...py[1], "-m", "venv", path.join(API_DIR, ".venv")]);
  }
  log("Memasang paket API...");
  run(VENV_PY, ["-m", "pip", "install", "-q", "-r", path.join(API_DIR, "requirements.txt")]);

  if (!fs.existsSync(path.join(WEB_DIR, "node_modules"))) {
    log("Memasang paket web (npm ci)...");
    run(NPM, ["ci"], { cwd: WEB_DIR });
  } else {
    log("Paket web sudah terpasang");
  }
  log("Selesai. Jalankan: npm run dev");
}

function portFree(port, host) {
  return new Promise((resolve) => {
    const srv = net.createServer();
    srv.once("error", () => resolve(false));
    srv.once("listening", () => srv.close(() => resolve(true)));
    srv.listen(port, host);
  });
}

function lanAddresses() {
  return Object.values(os.networkInterfaces())
    .flat()
    .filter((i) => i && i.family === "IPv4" && !i.internal)
    .map((i) => i.address);
}

async function serve(mode) {
  if (!fs.existsSync(VENV_PY) || !fs.existsSync(path.join(WEB_DIR, "node_modules"))) {
    die("Belum dipasang. Jalankan dulu: npm run setup");
  }
  if (!fs.existsSync(path.join(ROOT, ".env"))) die("File .env belum ada. Jalankan dulu: npm run setup");

  refreshWindowsPath();
  const env = readEnv();
  const apiPort = Number(env.API_PORT || 8000);
  const webPort = Number(env.WEB_PORT || 3000);
  if (!(await portFree(apiPort, "127.0.0.1"))) die(`Port API ${apiPort} sedang dipakai aplikasi lain. Ubah API_PORT di .env.`);
  if (!(await portFree(webPort, "0.0.0.0"))) die(`Port web ${webPort} sedang dipakai aplikasi lain. Ubah WEB_PORT di .env.`);

  if (mode === "start") {
    log("Membangun web...");
    run(NPM, ["run", "build"], { cwd: WEB_DIR });
  }

  const children = [];
  const launch = (name, cmd, args, cwd) => {
    const child = spawn(cmd, args, { cwd, shell: WIN && cmd.endsWith(".cmd"), stdio: ["ignore", "pipe", "pipe"] });
    const pipe = (stream) =>
      stream.on("data", (d) =>
        String(d)
          .split(/\r?\n/)
          .filter(Boolean)
          .forEach((l) => console.log(`\x1b[36m[${name}]\x1b[0m ${l}`)),
      );
    pipe(child.stdout);
    pipe(child.stderr);
    child.on("exit", (code) => {
      if (!stopping) {
        console.error(`\x1b[31m[${name}] berhenti (kode ${code}). Menghentikan yang lain.\x1b[0m`);
        stop(1);
      }
    });
    children.push(child);
  };

  let stopping = false;
  const stop = (code = 0) => {
    stopping = true;
    for (const c of children) {
      if (c.exitCode !== null) continue;
      if (WIN) spawnSync("taskkill", ["/PID", String(c.pid), "/T", "/F"], { stdio: "ignore" });
      else c.kill("SIGTERM");
    }
    setTimeout(() => process.exit(code), 300);
  };
  process.on("SIGINT", () => stop(0));
  process.on("SIGTERM", () => stop(0));

  launch("api", VENV_PY, ["-m", "app.main"], API_DIR);
  launch("web", NPM, ["run", mode === "start" ? "start" : "dev"], WEB_DIR);

  log(`Membuka: http://localhost:${webPort}`);
  for (const ip of lanAddresses()) log(`Dari komputer lain: http://${ip}:${webPort}`);
  log("Tekan Ctrl+C untuk menghentikan.");
}

const cmd = process.argv[2];
if (cmd === "setup") setup();
else if (cmd === "dev" || cmd === "start") await serve(cmd);
else die("Pakai: node scripts/spectrameet.mjs setup | dev | start");
