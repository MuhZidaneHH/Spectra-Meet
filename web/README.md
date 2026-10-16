# web

Antarmuka SpectraMeet (Next.js + TypeScript + Tailwind). Berjalan bersama API (`../api`).

- Pengaturan (port web dan API) dibaca dari `.env` di akar repo, bukan dari folder ini.
- `npm run dev` menjalankan server pengembangan di port `WEB_PORT` (bawaan 3000).
- Semua alamat `/api/*` diteruskan ke API, jadi browser hanya bicara ke satu alamat.
- Versi Next.js ini berbeda dari yang umum dikenal. Dokumentasinya ada di `node_modules/next/dist/docs/`.
