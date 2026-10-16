# SpectraMeet MVP 1

Ubah rekaman meeting menjadi transkrip per pembicara dan ringkasan. Berjalan di Windows dan Linux, tanpa login dan tanpa database eksternal.

> README ini ditulis bersama oleh Dev 1 dan Dev 2. Bagian **Web dan API** dari Dev 1. Bagian **Pipeline** menunggu Dev 2.

## Struktur

```
web/        Antarmuka (Next.js + TypeScript + Tailwind)       Dev 1
api/        Backend (FastAPI + SQLite)                         Dev 1
pipeline/   Mesin pemroses AI (WhisperX + LLM)                 Dev 2
data/       Audio, hasil, database (dibuat otomatis, tidak masuk git)
.env        Konfigurasi Anda (tidak masuk git)
```

## Kebutuhan

| Perangkat lunak | Versi | Dipakai oleh |
|---|---|---|
| Git | bebas | semua |
| Node.js | 20.9 atau lebih baru (LTS) | web |
| Python | 3.10 atau lebih baru | API |
| FFmpeg, Python 3.10-3.11 khusus pipeline | lihat bagian Pipeline | pipeline (Dev 2) |

Di Linux (Debian/Ubuntu) paket venv Python sering terpisah: `sudo apt install python3-venv`.

## Konfigurasi: satu file saja

Semua pengaturan (port, kunci API, model, folder data, batas unggahan) ada di **`.env`** di akar repo.

1. Salin `.env.example` menjadi `.env`.
2. Isi nilai yang kosong. Setiap variabel dijelaskan di `.env.example`: siapa yang memakainya, cara mendapatkan nilainya, dan apakah wajib.
3. **Restart aplikasi** setelah mengubah `.env`. Perubahan tidak berlaku sebelum restart.

Selama `USE_MOCK_PIPELINE=true` (bawaan), aplikasi memakai data contoh dan tidak butuh kunci apa pun.

Kunci yang dibutuhkan pipeline asli:

| Variabel | Dari mana |
|---|---|
| `LLM_API_KEY` | https://aistudio.google.com/apikey (gratis) |
| `LLM_MODEL` | Model Gemini yang tersedia di paket gratis: https://ai.google.dev/gemini-api/docs/models |
| `HF_TOKEN` | https://huggingface.co/settings/tokens, lalu setujui lisensi pyannote |

## Web dan API (Dev 1)

### Cara tercepat: satu perintah

Dari akar repo. Sama di Windows, Linux, dan macOS (butuh Node.js dan Python terpasang):

```bash
npm run setup   # sekali di awal: membuat .env, lingkungan Python API, dan memasang paket web
npm run dev     # menjalankan API + web, mode pengembangan
npm start       # membangun web lalu menjalankan API + web, mode server (untuk VM)
```

Skrip menampilkan alamat yang bisa dibuka (juga dari komputer lain), memberi tahu bila port bentrok, dan menghentikan API dan web bersamaan dengan `Ctrl+C`. Pemasangan ulang aman: `npm run setup` tidak menimpa `.env` dan tidak memasang ulang yang sudah ada. Skrip ini belum memasang pipeline AI (FFmpeg, WhisperX), yang disiapkan Dev 2.

Bagian di bawah adalah cara manual yang melakukan hal yang sama langkah demi langkah.

### Cara manual (tanpa skrip)

Pemasangan sekali di awal, dari akar repo setelah `git clone`.

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env

cd api
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..\web
npm ci
cd ..
```

**Linux / macOS (bash)**

```bash
cp .env.example .env

cd api
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ../web
npm ci
cd ..
```

### Menjalankan (dua terminal)

**Windows (PowerShell)**

```powershell
# Terminal 1: API (port dari API_PORT)
cd api
.\.venv\Scripts\python.exe -m app.main

# Terminal 2: Web (port dari WEB_PORT)
cd web
npm run dev
```

**Linux / macOS (bash)**

```bash
# Terminal 1: API (port dari API_PORT)
cd api
.venv/bin/python -m app.main

# Terminal 2: Web (port dari WEB_PORT)
cd web
npm run dev
```

Buka `http://localhost:<WEB_PORT>` (bawaan 3000). Browser hanya bicara ke web, dan web meneruskan `/api/*` ke API.

Jika port bentrok dengan aplikasi lain, ubah `WEB_PORT` atau `API_PORT` di `.env` dan jalankan ulang.

### Menjalankan di server atau VM

Di server pakai mode produksi (lebih cepat dan tanpa pembatasan asal akses mode pengembangan). Cukup:

```bash
npm start          # dari akar repo: build web, lalu jalankan API dan web
```

Secara manual: `npm run build` lalu `npm start` di folder `web`, dan `python -m app.main` di folder `api`. Hal yang perlu diperhatikan:

- Web mendengarkan semua alamat jaringan pada `WEB_PORT`. API hanya mendengarkan `127.0.0.1`, jadi hanya port web yang perlu dibuka di firewall.
- **Tidak ada login.** Siapa pun yang bisa menjangkau port web dapat mengunggah audio dan memakai kuota Gemini Anda. Batasi lewat firewall atau VPN.
- **Merekam dari mikrofon hanya jalan di `localhost` atau HTTPS.** Lewat `http://IP-SERVER:3000` tombol Rekam tidak berfungsi (unggah file tetap normal). Untuk mencoba merekam, buat terowongan SSH dari laptop Anda lalu buka `http://localhost:3000` di laptop:

  ```bash
  ssh -L 3000:localhost:3000 pengguna@ip-server
  ```
- Proses akan mati saat sesi terminal ditutup. Untuk uji singkat gunakan `tmux` atau `screen`, atau jalankan sebagai layanan (systemd).

### Perintah pengembangan

**Windows (PowerShell)**

```powershell
# Tes API (dari folder api)
.\.venv\Scripts\python.exe -m pytest

# Perbarui tipe web setelah mengubah api/app/schemas.py (API harus berjalan)
cd web; npm run gen:types

# Lint dan build web
npm run lint; npm run build
```

**Linux / macOS (bash)**

```bash
# Tes API (dari folder api)
.venv/bin/python -m pytest

# Perbarui tipe web setelah mengubah api/app/schemas.py (API harus berjalan)
cd web && npm run gen:types

# Lint dan build web
npm run lint && npm run build
```

### Daftar periksa: apakah ini jalan di mesin lain?

Setelah `git clone` dan pemasangan di atas, dengan `.env` bawaan (pipeline tiruan):

1. `pytest` di folder `api` berakhir hijau semua (17 tes lulus).
2. `npm run lint` dan `npm run build` di folder `web` selesai tanpa galat.
3. `npm run dev` (atau `npm start`), lalu buka alamat yang ditampilkan: chip di header berbunyi **"Mesin siap · Pipeline tiruan"**.
4. Unggah file audio apa pun, klik Proses: kelima langkah berjalan dan selesai dalam sekitar 10 detik, lalu "Lihat hasil" menampilkan ringkasan dan transkrip contoh.
5. Di halaman Hasil, putar audio dan klik sebuah kalimat: audio melompat ke posisi itu.

Bila ada yang gagal, klik chip status mesin di header: panel itu menyebut apa yang kurang dan variabel `.env` mana yang perlu diisi.

## Pipeline (Dev 2)

_Menunggu Dev 2: setup FFmpeg (Windows dan Linux), venv pipeline, dan cara menjalankan. API mencari Python pipeline di `pipeline/.venv/Scripts/python.exe` (Windows) atau `pipeline/.venv/bin/python` (Linux) kecuali `PIPELINE_PYTHON` di `.env` diisi._
