# Kontrak JSON SpectraMeet MVP 1

**Versi skema:** `1.0`
**Status:** usulan final dari PM, **menunggu persetujuan Dev 1 dan Dev 2** (tanda tangan di bagian bawah).
**Contoh lengkap:** [`contoh-hasil.json`](contoh-hasil.json)

Kontrak ini adalah satu-satunya kesepakatan bentuk data antara **pipeline (Dev 2)** dan **web/API (Dev 1)**. Kalau ada perubahan, ubah file ini lebih dulu, naikkan `schema_version`, baru ubah kode.

## Aturan umum

1. Nama kunci memakai bahasa Inggris `snake_case`, kecuali isi ringkasan (`ringkasan`, `keputusan`, `tugas`, `pertanyaan_terbuka`) yang mengikuti tampilan di UI.
2. Semua waktu dalam **detik** (angka desimal), dihitung dari awal audio.
3. Teks isi memakai bahasa asli rekaman. Kunci tidak diterjemahkan.
4. `speaker` selalu berupa ID stabil (`SPEAKER_00`, `SPEAKER_01`, ...). Nama tampilan ("Pembicara 1") ada di daftar `speakers`.
5. Bidang yang bisa kosong ditulis `null`, bukan dihapus. Daftar kosong ditulis `[]`.
6. `is_sample: true` hanya ada di berkas contoh. Pipeline sungguhan tidak mengisinya.
7. Skema di Python didefinisikan dengan Pydantic (`pipeline/spectrameet_pipeline/schema.py`). Berkas ini mendokumentasikannya, dan tipe TypeScript dibuat otomatis dari OpenAPI. Kalau berbeda, Pydantic yang benar dan dokumen ini diperbaiki.

## 1. Hasil akhir (`result`)

| Kunci | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `schema_version` | string | ya | `"1.0"` |
| `is_sample` | boolean | tidak | Hanya di contoh |
| `meeting.id` | string | ya | ID meeting |
| `meeting.title` | string | ya | Judul, boleh diubah pengguna |
| `meeting.audio_file` | string | ya | Nama berkas audio asli |
| `meeting.duration_sec` | number | ya | Durasi audio |
| `meeting.language` | string | ya | Kode bahasa hasil deteksi, misalnya `id`, `en` |
| `meeting.created_at` | string | ya | ISO 8601 dengan zona waktu |
| `pipeline.whisper_model` | string | ya | Model suara-ke-teks yang dipakai |
| `pipeline.diarization_model` | string | ya | Model identifikasi pembicara |
| `pipeline.llm_model` | string | ya | Model ringkasan |
| `pipeline.timings_sec` | object | ya | Waktu per tahap: `audio`, `vad`, `stt`, `diarization`, `summary` |
| `speakers[]` | array | ya | `id` dan `label` |
| `segments[]` | array | ya | `start`, `end`, `speaker`, `text`. Urut menurut `start` |
| `summary.ringkasan` | string | ya | 2–4 kalimat |
| `summary.keputusan[]` | array | ya | `text`, `timestamp_sec` |
| `summary.tugas[]` | array | ya | `owner_speaker` (ID atau `null`), `text`, `due_text` (teks bebas atau `null`), `timestamp_sec` |
| `summary.pertanyaan_terbuka[]` | array | ya | `text`, `timestamp_sec` |
| `warnings[]` | array | ya | `code`, `message`, `at_sec` (boleh `null`) |

**Kode peringatan yang disepakati:** `OVERLAP_SPEECH` (suara tumpang tindih), `LOW_AUDIO_QUALITY`, `LANGUAGE_MIXED`, `SHORT_AUDIO`. Kode baru ditambahkan di sini lebih dulu.

**Aturan isi:**
- `owner_speaker: null` berarti penanggung jawab tidak jelas. UI menampilkan "Belum ditentukan".
- `due_text` disimpan sebagai teks yang diucapkan ("Besok", "Rabu"). Mengubahnya menjadi tanggal dikerjakan di MVP 2.
- Ringkasan tidak boleh memuat fakta yang tidak ada di transkrip. Aturan ini dijaga lewat prompt (milik PM).

## 2. Status job (`job`)

Dipakai API untuk halaman Proses. Dicatat di tabel `jobs`.

```json
{
  "id": "job_0001",
  "meeting_id": "mtg_0001",
  "status": "running",
  "stage": "stt",
  "stage_index": 3,
  "stage_total": 5,
  "elapsed_sec": 214.0,
  "error": null
}
```

| Kunci | Nilai |
|---|---|
| `status` | `queued`, `running`, `done`, `failed` |
| `stage` | `audio`, `vad`, `stt`, `diarization`, `summary` |
| `stage_index` / `stage_total` | 1–5 dari 5 |
| `elapsed_sec` | Waktu berjalan. **Tidak ada ETA** di MVP 1 karena belum bisa diprediksi andal |
| `error` | `null`, atau objek di bawah |

Objek `error` saat `failed`:

```json
{
  "stage": "diarization",
  "code": "HF_TOKEN_MISSING",
  "message": "Token Hugging Face belum diisi di .env",
  "log_tail": "baris terakhir log untuk ditampilkan di layar Gagal"
}
```

**Kode galat yang disepakati:** `AUDIO_UNREADABLE`, `FFMPEG_NOT_FOUND`, `HF_TOKEN_MISSING`, `MODEL_DOWNLOAD_FAILED`, `OUT_OF_MEMORY`, `LLM_AUTH_FAILED`, `LLM_TIMEOUT`, `LLM_BAD_OUTPUT`, `UNKNOWN`. Pesan harus bisa dipahami pengguna non-teknis; detail teknis masuk `log_tail`.

## 3. Endpoint API

| Metode | Path | Keterangan |
|---|---|---|
| `POST` | `/meetings` | Unggah audio, buat meeting dan job (`queued`). Mengembalikan `meeting_id`, `job_id` |
| `GET` | `/jobs/{job_id}` | Status job (bentuk di atas) |
| `GET` | `/meetings/{id}/result` | Hasil akhir. `409` jika belum selesai |
| `GET` | `/meetings/{id}/audio` | Berkas audio untuk pemutar |

Format audio yang diterima di MVP 1: `wav`, `mp3`, `m4a`, `mp4` (diekstrak audionya). Batas ukuran awal: 500 MB (usulan, bisa diubah).

## 4. Perubahan kontrak

1. Usul perubahan ditulis di Pull Request yang mengubah berkas ini.
2. Dev 1 dan Dev 2 sama-sama menyetujui.
3. Perubahan yang menghapus atau mengganti nama kunci menaikkan versi mayor (`2.0`). Penambahan kunci opsional menaikkan versi minor (`1.1`).

## Persetujuan

| Peran | Nama | Setuju | Tanggal |
|---|---|---|---|
| PM | | | |
| Dev 1 | | | |
| Dev 2 | | | |
