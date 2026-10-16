"use client";

import { useEffect, useState } from "react";

// Halaman "hello": membuktikan web dapat menjangkau API lewat /api.
export default function Home() {
  const [status, setStatus] = useState("memeriksa API...");

  useEffect(() => {
    fetch("/api/ping")
      .then((r) => r.json())
      .then((d) => setStatus(`API tersambung (pipeline tiruan: ${d.mock_pipeline ? "ya" : "tidak"})`))
      .catch(() => setStatus("API tidak terjangkau"));
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">SpectraMeet</h1>
      <p className="mt-2">{status}</p>
    </main>
  );
}
