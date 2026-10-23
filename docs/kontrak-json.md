# Kontrak JSON SpectraMeet MVP 1

**Versi skema:** `1.1` (usulan PM, 23 Okt 2026)
**Status:** **menunggu persetujuan PM, Dev 1, dan Dev 2** (tanda tangan di bagian bawah). Versi `1.0` adalah dasar yang dipakai kode saat ini. Semua perubahan 1.1 bersifat **menambah atau mendokumentasikan kenyataan kode**, tidak ada kunci yang dihapus atau diganti nama, sehingga web yang memahami `1.x` tetap jalan.
**Contoh lengkap:** [`contoh-hasil.json`](contoh-hasil.json)

Kontrak ini adalah satu-satunya kesepakatan bentuk data antara **pipeline (Dev 2)** dan **web/API (Dev 1)**. Kalau ada perubahan, ubah berkas ini lebih dulu, naikkan `schema_version`, baru ubah kode.

## Perubahan dari 1.0

| # | Perubahan | Alasan |
|---|---|---|
| 1 | Endpoint ditulis ulang **berpusat pada meeting**, sesuai API yang sudah dibangun (bagian 3) | Fungsinya setara dengan rancangan job. Dokumen disesuaikan dengan kode, bukan sebaliknya |
| 2 | Kode galat memakai **daftar milik pipeline** (`errors.py`), ditambah `OUT_OF_MEMORY` yang juga dikenali API (bagian 2) | Sudah ada di kode dan dipetakan. Menghapus dua daftar yang saling berbeda |
| 3 | Bentuk hasil Dev 2 (datar) diakui sebagai **format sementara** yang diterjemahkan adapter API (bagian 4) | Usulan PM: adapter dipertahankan selama MVP 1, Dev 2 menyamakan sebelum MVP 2 |
| 4 | Ditambah kode peringatan `REPEATED_TEXT` dan `LOW_TRANSCRIPT_QUALITY` (bagian 1) | Uji 22 Okt: 15–18% kata pada rapat panjang adalah pengulangan tak diucapkan |
| 5 | Ditambah kunci opsional `repeat_count` pada segmen (bagian 1) | Menampilkan rangkaian segmen identik sebagai satu baris |
| 6 | Ditambah aturan **data mentah tidak boleh dibuang** (bagian 4) | Penyaringan hanya untuk tampilan |
| 7 | `timestamp_sec`, `speaker`, dan `warnings` kosong diakui sah di MVP 1 | Pipeline belum mengisinya |
| 8 | Format dan batas unggahan mengikuti `.env` | `.env.example` adalah sumber kebenaran |

## Aturan umum

1. Nama kunci memakai bahasa Inggris `snake_case`, kecuali isi ringkasan (`ringkasan`, `keputusan`, `tugas`, `pertanyaan_terbuka`) yang mengikuti tampilan di UI.
2. Semua waktu dalam **detik** (angka desimal), dihitung dari awal audio.
3. Teks isi memakai bahasa asli rekaman. Kunci tidak diterjemahkan.
4. `speaker` berupa ID stabil (`SPEAKER_00`, `SPEAKER_01`, ...) atau `null` bila pembicara tidak dikenali (pipeline menulis `UNKNOWN`, adapter menjadikannya `null`). Nama tampilan ("Pembicara 1") ada di daftar `speakers`.
5. Bidang yang bisa kosong ditulis `null`, bukan dihapus. Daftar kosong ditulis `[]`.
6. `is_sample: true` hanya ada di berkas contoh. Pipeline sungguhan tidak mengisinya.
7. Skema di Python didefinisikan dengan Pydantic. Berkas ini mendokumentasikannya. Kalau berbeda, kode yang benar dan dokumen ini diperbaiki.
8. Kunci tambahan yang tidak dikenal diterima dan diteruskan apa adanya (perilaku `api/app/contract.py`).

## 1. Hasil akhir (`result`)

| Kunci | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `schema_version` | string | ya | `"1.1"` (web menerima semua `1.x`) |
| `is_sample` | boolean | tidak | Hanya di contoh |
| `meeting.id` | string | ya | ID meeting |
| `meeting.title` | string | ya | Judul, boleh diubah pengguna. Di MVP 1 sama dengan nama berkas |
| `meeting.audio_file` | string | ya | Nama berkas audio asli |
| `meeting.duration_sec` | number | ya | Durasi audio |
| `meeting.language` | string | ya | Kode bahasa, misalnya `id`, `en` |
| `meeting.created_at` | string | ya | ISO 8601 dengan zona waktu |
| `pipeline.whisper_model` | string | ya | Model suara-ke-teks yang dipakai |
| `pipeline.diarization_model` | string | ya | Model identifikasi pembicara |
| `pipeline.llm_model` | string | ya | Model ringkasan |
| `pipeline.timings_sec` | object | ya | Waktu per tahap: `audio`, `vad`, `stt`, `diarization`, `summary` |
| `speakers[]` | array | ya | `id` dan `label` |
| `segments[]` | array | ya | `start`, `end`, `speaker` (boleh `null`), `text`. Urut menurut `start`. Opsional: `repeat_count` |
| `summary.ringkasan` | string | ya | 3–6 kalimat |
| `summary.keputusan[]` | array | ya | `text`, `timestamp_sec` (boleh `null`) |
| `summary.tugas[]` | array | ya | `text`, `owner_speaker` (ID atau `null`), `due_text` (teks bebas atau `null`), `timestamp_sec` (boleh `null`). Opsional: `owner_name` |
| `summary.pertanyaan_terbuka[]` | array | ya | `text`, `timestamp_sec` (boleh `null`) |
| `summary_status` | string | tidak | `ok`, `skipped`, atau `failed`. Transkrip tetap ada walau ringkasan gagal |
| `summary_error` | string | tidak | Alasan bila `summary_status` bukan `ok` |
| `warnings[]` | array | ya | `code`, `message`, `at_sec` (boleh `null`). Boleh `[]` |

**Kunci opsional baru dan yang sudah ada di kode**
- `tugas[].owner_name`: nama orang yang **disebut** di transkrip bila bukan ID pembicara. Pipeline mengisi `owner` dengan nama, adapter menaruhnya di sini, dan `owner_speaker` tetap `null` bila nama tidak cocok dengan ID.
- `segments[].repeat_count` (**baru**, bilangan bulat ≥ 2): rangkaian segmen identik berurutan diringkas menjadi satu segmen. Nilainya jumlah asli. Hanya ada pada hasil yang sudah disaring untuk tampilan (lihat bagian 4).

**Kode peringatan yang disepakati**

| Kode | Arti |
|---|---|
| `OVERLAP_SPEECH` | Suara tumpang tindih, label pembicara bisa tertukar |
| `LOW_AUDIO_QUALITY` | Audio berkualitas rendah |
| `LANGUAGE_MIXED` | Bahasa campur |
| `SHORT_AUDIO` | Audio sangat pendek |
| `REPEATED_TEXT` (**baru**) | Ada teks berulang tak wajar (kata atau segmen yang sama berkali-kali). `at_sec` diisi awal kemunculan pertama bila diketahui. Diduga kesalahan mesin, bukan ucapan |
| `LOW_TRANSCRIPT_QUALITY` (**baru**) | Transkrip kemungkinan tidak dapat dipercaya penuh (sebagian besar segmen sangat pendek, label pembicara berganti sangat cepat, atau banyak pengulangan). Dipakai web untuk menampilkan catatan "kualitas rendah" |

Kode baru ditambahkan di sini lebih dulu. Aturan pemakaian dan ambang untuk menghasilkan peringatan ditetapkan Dev 1 dan Dev 2, lalu dicatat di berkas ini.

**Aturan isi**
- `owner_speaker: null` dan `owner_name` kosong berarti penanggung jawab tidak jelas. UI menampilkan "Belum ditentukan".
- Peran umum ("panitia", "peserta", "tim") dan kata ganti ("saya") **bukan** pemilik tugas. Aturan ini dijaga di prompt (milik PM).
- `due_text` disimpan sebagai teks yang diucapkan ("Besok", "Rabu"). Mengubahnya menjadi tanggal dikerjakan di MVP 2.
- Ringkasan tidak boleh memuat fakta yang tidak ada di transkrip. Aturan ini dijaga lewat prompt. Perbaikan kata yang jelas salah dengar oleh LLM tetap perlu diwaspadai, karena itu tebakan.
- Kontrak **tidak menjamin ketepatan transkrip**. Mutu bergantung pada model dan audio. Web boleh menampilkan peringatan, tetapi tidak boleh menyiratkan transkrip pasti benar.

## 2. Status proses (`progress`) dan galat

Pipeline menulis `progress.json` selama berjalan. API membacanya dan menyajikan versi ringkas di respons meeting (bagian 3). Bentuk berkas pipeline (lihat `pipeline/spectrameet_pipeline/schema.py`):

```json
{
  "job_id": "…",
  "status": "running",
  "step": 3,
  "percent": 40.0,
  "steps": [
    { "id": 1, "name": "Menyiapkan audio", "status": "done", "started_at": 0, "ended_at": 0 }
  ],
  "resumed_from": null,
  "started_at": 0,
  "updated_at": 0,
  "error": null
}
```

| Kunci | Nilai |
|---|---|
| `status` (pipeline) | `running`, `done`, `failed` |
| `steps[].status` | `pending`, `running`, `done`, `skipped`, `failed` |
| `step` | 1–5. Tahap yang sedang atau terakhir berjalan |
| `resumed_from` | `null`, atau tahap pertama yang dihitung ulang saat "Coba lagi" |
| `error` | `null`, atau `{ code, message, step, detail }` |

Tahap: 1 Menyiapkan audio, 2 Mendeteksi suara, 3 Mengubah suara ke teks, 4 Mengenali pembicara, 5 Menyusun kesimpulan. **Tidak ada ETA** di MVP 1 karena belum bisa diprediksi andal; yang ditampilkan adalah waktu berjalan.

Status **meeting** (di database dan API): `uploaded`, `processing`, `done`, `failed`, `cancelled`.

**Kode galat yang disepakati** (sumber: `pipeline/spectrameet_pipeline/errors.py`):

| Kode | Arti |
|---|---|
| `AUDIO_NOT_FOUND` | Berkas audio tidak ditemukan |
| `AUDIO_UNREADABLE` | Audio tidak bisa dibaca atau rusak |
| `FFMPEG_MISSING` | FFmpeg belum terpasang |
| `HF_TOKEN_MISSING` | Token Hugging Face belum diisi atau ditolak |
| `MODEL_UNAVAILABLE` | Model tidak bisa diunduh atau diakses (termasuk lisensi belum disetujui) |
| `OUT_OF_MEMORY` | Memori habis. API juga mengenalinya dari crash proses tanpa galat tertulis |
| `CANCELLED` | Dihentikan pengguna |
| `LLM_NOT_CONFIGURED` | Kunci atau model LLM belum diisi |
| `LLM_AUTH` | Kunci LLM ditolak |
| `LLM_MODEL_NOT_FOUND` | Nama model LLM tidak ditemukan |
| `LLM_QUOTA` | Kuota LLM habis atau terlalu cepat |
| `LLM_OVERLOADED` | Layanan LLM sibuk, sudah dicoba ulang otomatis |
| `LLM_UNREACHABLE` | Tidak bisa terhubung ke LLM |
| `LLM_BAD_OUTPUT` | Jawaban LLM bukan JSON yang sesuai, juga setelah dicoba ulang |
| `LLM_FAILED` | Ringkasan gagal karena galat tak terduga |
| `UNKNOWN` | Galat lain |

Pesan harus bisa dipahami pengguna non-teknis. Detail teknis masuk `detail` dan cuplikan log. Kegagalan tahap 5 **tidak** membatalkan transkrip: status ringkasan `failed` atau `skipped`, dan tahap 1–4 tetap dipakai.

## 3. Endpoint API

Semua di bawah awalan `/api`. Berpusat pada **meeting** (menggantikan rancangan `/jobs/{job_id}` di 1.0).

| Metode | Path | Keterangan |
|---|---|---|
| `GET` | `/ping` | Cek hidup |
| `GET` | `/config` | Pilihan form, format dan batas unggahan, interval polling (dari `.env`) |
| `GET` | `/health` | Status mesin: apa yang siap dan apa yang kurang |
| `POST` | `/meetings` | Unggah audio, buat meeting (`uploaded`). Menolak format salah (400), berkas kosong (400), terlalu besar (413), pilihan tidak dikenal (422) |
| `GET` | `/meetings/{id}` | Detail dan progres: `status`, `current_step`, `error_step`, `error_message`, `progress` (`percent`, `steps`, `error`) |
| `POST` | `/meetings/{id}/start` | Mulai proses. `409` bila ada pekerjaan lain berjalan |
| `POST` | `/meetings/{id}/retry` | Coba lagi dari tahap yang gagal (dari awal bila dibatalkan) |
| `POST` | `/meetings/{id}/cancel` | Menghentikan pipeline beserta turunannya |
| `GET` | `/meetings/{id}/result` | Hasil akhir sesuai bagian 1. `409` bila belum selesai, `500` dengan nama field bila isinya menyimpang |
| `GET` | `/meetings/{id}/audio` | Berkas audio, mendukung `Range` untuk pemutar |

Format audio yang diterima dan batas ukuran **mengikuti `.env`** (`ALLOWED_EXTENSIONS`, `MAX_UPLOAD_MB`). Nilai bawaan saat ini: `mp3, wav, m4a, webm, ogg, flac` dan 200 MB. Pipeline hanya memproses satu pekerjaan pada satu waktu.

## 4. Format sementara pipeline dan aturan data mentah

**Format sementara.** Selama MVP 1, pipeline menulis hasil berbentuk datar berbahasa Inggris (`summary`, `decisions`, `tasks[description, owner, due]`, `open_questions`, ditambah `segments`, `language`, `duration`, `summary_status`, `summary_error`). Adapter di `api/app/contract.py` menerjemahkannya ke bentuk kontrak di bagian 1. Hasil yang sudah memuat `schema_version` diteruskan tanpa diubah. **Target:** sebelum MVP 2, pipeline (Dev 2) menulis bentuk kontrak langsung, lalu adapter dihapus.

**Data mentah tidak boleh dibuang.** `hasil.json` yang ditulis pipeline tidak boleh diubah oleh API atau web. Penyaringan untuk tampilan (meringkas segmen identik berulang dengan `repeat_count`, memotong teks loop yang sangat panjang, menyembunyikan segmen kosong) dilakukan **saat disajikan**, di salinan. Alasannya, ucapan asli yang tertimpa pengulangan tidak bisa dipulihkan dari tampilan yang sudah disaring, dan data mentah diperlukan untuk menilai mutu serta memperbaiki pipeline.

## 5. Perubahan kontrak

1. Usul perubahan ditulis di Pull Request yang mengubah berkas ini.
2. Dev 1 dan Dev 2 sama-sama menyetujui.
3. Perubahan yang menghapus atau mengganti nama kunci menaikkan versi mayor (`2.0`). Penambahan kunci opsional menaikkan versi minor (`1.x`).
4. Setelah `1.1` disetujui: `SCHEMA_VERSION` di `api/app/contract.py` dinaikkan ke `"1.1"`, dan tipe web (`web/src/lib/types.ts`) menambah `repeat_count` dan `owner_name` bila belum ada.

## Persetujuan

| Peran | Nama | Setuju | Tanggal |
|---|---|---|---|
| PM | | | |
| Dev 1 | | | |
| Dev 2 | | | |
