# Kontrak JSON pipeline

**Status: DRAF dari Dev 2, menunggu persetujuan PM dan Dev 1.** Sumber kebenarannya adalah model Pydantic di `pipeline/spectrameet_pipeline/schema.py`. Bila dokumen ini berbeda dengan kode, kodelah yang benar. Contoh lengkap: `docs/contoh-hasil.json`.

Pipeline dijalankan sebagai proses terpisah dan berbicara dengan API lewat dua berkas di `data/hasil/<job_id>/`:

| Berkas | Ditulis | Isi |
|---|---|---|
| `progress.json` | terus-menerus selama berjalan | keadaan lima tahap |
| `hasil.json` | sekali, di akhir | transkrip dan kesimpulan |
| `audio.wav` | tahap 1 | audio standar 16 kHz mono (bukan untuk pemutar web) |
| `audio.json`, `stt.json`, `segmen.json` | tiap tahap selesai | hasil antar tahap untuk mulai ulang (lihat "Coba lagi") |

Menjalankan: `python -m spectrameet_pipeline.cli <audio> --job-id <id> [--language id-en|id|en] [--speakers auto|2|3|4|5+] [--resume]`.
Kode keluar proses: `0` bila `hasil.json` tertulis, `1` bila tahap 1-4 gagal, `130` bila dibatalkan dengan Ctrl+C.

## Coba lagi (`--resume`)

Setiap tahap menyimpan hasilnya. Menjalankan perintah yang sama dengan `--resume` dan `--job-id` yang sama melewati tahap yang hasilnya masih berlaku, jadi kegagalan di tahap akhir tidak mengulang transkripsi yang makan beberapa menit. Diukur pada klip 5 menit: dari awal ±190 dtk, lanjut dari tahap 4 ±104 dtk, hanya ringkasan ±8 dtk.

- Hasil dipakai ulang hanya bila audio (jalur, ukuran, waktu ubah), bahasa, `WHISPER_MODEL`, `ALIGN`, dan (untuk tahap 4) jumlah pembicara tidak berubah. Bila ada yang berubah, tahap itu dan sesudahnya dihitung ulang. File checkpoint yang rusak dianggap tidak ada.
- Tahap 5 (ringkasan) selalu dijalankan ulang saat `--resume`.
- Tanpa `--resume`, semuanya dihitung dari awal dan checkpoint lama dibuang.
- `progress.json` memuat `resumed_from`: tahap pertama yang benar-benar dihitung ulang (2, 4, atau 5). Tahap sebelumnya langsung `done`. Bernilai `null` pada pekerjaan baru.
- Tombol "Coba lagi" di web = jalankan ulang perintah dengan `--resume`. Tombol "Proses ulang" (bila ada) = tanpa `--resume`.


## progress.json

```json
{
  "job_id": "abc123",
  "status": "running",
  "step": 3,
  "percent": 42.0,
  "steps": [
    {"id": 1, "name": "Menyiapkan audio",       "status": "done",    "started_at": 1760000000.1, "ended_at": 1760000000.4},
    {"id": 2, "name": "Mendeteksi suara",       "status": "done",    "started_at": 1760000000.4, "ended_at": 1760000026.0},
    {"id": 3, "name": "Mengubah suara ke teks", "status": "running", "started_at": 1760000026.0, "ended_at": null},
    {"id": 4, "name": "Mengenali pembicara",    "status": "pending", "started_at": null, "ended_at": null},
    {"id": 5, "name": "Menyusun kesimpulan",    "status": "pending", "started_at": null, "ended_at": null}
  ],
  "started_at": 1760000000.0,
  "updated_at": 1760000031.2,
  "error": null
}
```

- `status` pekerjaan: `running`, `done`, `failed`. API cukup mengulang membaca berkas ini.
- `step` adalah tahap yang sedang atau terakhir berjalan (1-5). `percent` 0-100 untuk tahap itu, hanya perkiraan.
- `steps[].status`: `pending`, `running`, `done`, `skipped`, `failed`. Waktu dalam detik epoch; waktu berjalan = `now - started_at`.
- Berkas selalu valid. Ia ditulis lewat berkas sementara lalu diganti, jadi pembaca tidak pernah melihat JSON setengah jadi. Bila membaca gagal sesaat di Windows, ulangi.
- Tahap 2 (deteksi suara) berjalan bersama pemuatan model, jadi pada job pertama bisa memakan puluhan detik.

### Proses yang mati mendadak

Proses yang dihentikan paksa (mis. `terminate()` di Windows, atau laptop mati) tidak sempat menulis galat, sehingga `progress.json` tetap `running`. API sebaiknya menganggap pekerjaan mati bila proses sudah tidak ada, atau `updated_at` lebih dari 3 menit lalu (pemuatan model bisa diam sampai ±60 dtk). Setelah itu API boleh menawarkan "Coba lagi" (`--resume`).

### Galat

Bila `status` = `failed`, `error` terisi dan tahap terkait berstatus `failed`:

```json
{"code": "OUT_OF_MEMORY", "message": "Memori habis. Coba model Whisper lebih kecil di .env.", "step": 3, "detail": "teks teknis untuk log"}
```

`message` aman ditampilkan ke pengguna. `detail` hanya untuk log. `code` tetap:

| Kode | Arti |
|---|---|
| `AUDIO_NOT_FOUND` | file audio tidak ada |
| `FFMPEG_MISSING` | FFmpeg belum terpasang |
| `AUDIO_UNREADABLE` | audio rusak atau format tidak dikenali |
| `HF_TOKEN_MISSING` | `HF_TOKEN` kosong |
| `MODEL_UNAVAILABLE` | model tak bisa diunduh atau diakses (token, lisensi, atau jaringan) |
| `OUT_OF_MEMORY` | memori habis |
| `CANCELLED` | dihentikan pengguna (Ctrl+C) |
| `UNKNOWN` | galat tak terduga |

**Tahap 5 gagal tidak menggagalkan pekerjaan.** Transkrip tetap berguna, jadi `status` pekerjaan menjadi `done`, tahap 5 berstatus `failed`, dan `error` berisi alasannya dengan `step: 5`. Kode tahap 5: `LLM_AUTH`, `LLM_MODEL_NOT_FOUND`, `LLM_QUOTA`, `LLM_OVERLOADED` (Gemini sibuk; sudah dicoba ulang 3 kali otomatis), `LLM_UNREACHABLE`, `LLM_BAD_OUTPUT`, `LLM_FAILED`, `LLM_NOT_CONFIGURED`. Halaman Hasil sebaiknya menampilkan transkrip dan pesan galatnya, dengan tombol coba lagi untuk ringkasan.

## hasil.json

```json
{
  "version": 1,
  "language": "id",
  "duration": 312.4,
  "segments": [{"start": 0.4, "end": 7.9, "speaker": "SPEAKER_00", "text": "..."}],
  "summary_status": "ok",
  "summary_error": null,
  "summary": "...",
  "decisions": ["..."],
  "tasks": [{"description": "...", "owner": null, "due": null}],
  "open_questions": ["..."]
}
```

| Field | Tipe | Catatan |
|---|---|---|
| `version` | angka | naik bila bentuk berubah |
| `language` | teks | kode bahasa yang dipakai (`id`, `en`). Pilihan form "Indonesia + Inggris" diproses sebagai `id`. |
| `duration` | angka | detik |
| `segments[].start`, `end` | angka | detik dari awal audio. Dipakai untuk klik timestamp. Berurutan menurut `start`. |
| `segments[].speaker` | teks | `SPEAKER_00`, `SPEAKER_01`, ... atau `UNKNOWN`. Hanya penanda suara yang sama, bukan nama orang. |
| `segments[].text` | teks | tidak kosong |
| `summary_status` | `ok` / `skipped` / `failed` | lihat bawah |
| `summary_error` | teks atau null | alasan bila `skipped` atau `failed` |
| `summary` | teks atau null | null bila status bukan `ok` |
| `decisions`, `open_questions` | daftar teks | bisa kosong, itu normal |
| `tasks[].description` | teks | |
| `tasks[].owner`, `due` | teks atau null | null bila tidak disebut jelas di rekaman |

`summary_status`:
- `ok`: ringkasan, keputusan, tugas, dan pertanyaan terisi (daftar boleh kosong).
- `skipped`: tidak ada yang diringkas, yaitu `LLM_API_KEY` atau `LLM_MODEL` belum diisi, atau tidak ada ucapan terdeteksi. `summary` null.
- `failed`: panggilan LLM gagal. `summary` null dan `summary_error` berisi alasannya.

## Hal yang perlu disepakati

1. **Nama field berbahasa Inggris** (`segments`, `summary`, `decisions`, `tasks`, `open_questions`) mengikuti pemberian nama di kode. Label di antarmuka tetap bahasa Indonesia. Setuju?
2. **Nama pembicara** (rename) bukan bagian MVP 1, jadi `speaker` apa adanya.
3. **Hasil per kata** (`words`) tidak dikeluarkan. Cukup per kalimat untuk MVP 1.
4. **Batalkan**: pipeline mencatat `CANCELLED` bila menerima Ctrl+C (`KeyboardInterrupt`). `Popen.terminate()` di Windows tidak bisa ditangkap, jadi untuk tombol Batalkan, API yang menulis `failed` dengan kode `CANCELLED` setelah menghentikan proses. Perlu disepakati dengan Dev 1.
