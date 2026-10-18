"""Tampilkan model Gemini yang bisa dipakai untuk LLM_MODEL oleh kunci di .env.

    python daftar_model.py          semua model teks
    python daftar_model.py flash    hanya yang namanya memuat "flash"
"""

import sys

from google import genai

from spectrameet_pipeline.config import settings

if not settings.llm_api_key.strip():
    sys.exit("LLM_API_KEY belum diisi di .env")

client = genai.Client(api_key=settings.llm_api_key)
kata = sys.argv[1].lower() if len(sys.argv) > 1 else ""
for m in sorted(client.models.list(), key=lambda m: m.name):
    nama = m.name.removeprefix("models/")
    if "generateContent" in (m.supported_actions or []) and kata in nama.lower():
        print(nama)
