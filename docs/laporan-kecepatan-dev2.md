# Laporan kecepatan pipeline (Dev 2), tahap 2-4 tanpa alignment

Diukur 18 Okt 2026 di laptop Dev 2: Intel i9-14900HX (32 thread), RAM 64 GB, Windows 11.
Mode: CPU, `compute_type=int8`, WhisperX 3.8.6, `--language id`, `--no_align`, diarization `pyannote/speaker-diarization-community-1`.
Sumber audio: potongan dari satu rekaman nyata (`AKBP-Sesi-1-Audio.m4a`, 4 jam 12 menit), mono 16 kHz.

## Model `small`

| Klip | Durasi audio | Waktu proses | Rasio (waktu/durasi) | Memori puncak | Pembicara terdeteksi |
|---|---|---|---|---|---|
| uji-1menit | 60 dtk | 74,8 dtk | 1,25 | 2,9 GB | 1 |
| uji-a-5menit | 300 dtk | 147,1 dtk | 0,49 | 2,9 GB | 1 |
| uji-b-5menit | 300 dtk | 194,4 dtk | 0,65 | 2,9 GB | 2 |
| uji-c-5menit | 300 dtk | 213,0 dtk | 0,71 | 2,9 GB | 3 |

- Klip 1 menit lebih lambat per detik audio karena biaya muat model tetap (puluhan detik).
- Perkiraan kasar: rekaman 10 menit butuh sekitar 6-8 menit di CPU ini. Ini belum memasukkan alignment dan tahap LLM, dan belum diukur di laptop Dev 1.
- Model `tiny` pada klip 1 menit selesai 3 mnt 46 dtk, tetapi sebagian besar waktu itu adalah unduhan model diarization pertama kali, bukan inferensi.

## Temuan

1. **Pipeline berjalan di Windows**: token HF, lisensi pyannote, FFmpeg, transkripsi, dan label pembicara terbukti jalan.
2. **Unduhan model adalah hambatan terbesar**, bukan inferensi. Jaringan di sini 0,2-0,5 MB/s. Ukuran: `small` 461 MB, alignment Indonesia (`cahya/wav2vec2-large-xlsr-indonesian`) sekitar 1,2 GB. Setup dari nol butuh waktu lama, jadi README perlu menyebut ukurannya.
3. **Timeout unduhan bawaan terlalu pendek (10 dtk)** dan unduhan macet di 0 byte. Penyelesaian: `HF_HUB_DISABLE_XET=1` dan `HF_HUB_DOWNLOAD_TIMEOUT=120`. Sebaiknya skrip setup mengatur keduanya.
4. **Halusinasi pengulangan pada model small**: klip b memiliki satu frasa yang berulang puluhan kali (trigram yang sama muncul 87 kali). Perlu ditangani dengan parameter VAD atau `condition_on_previous_text=False`, sebelum LLM menerima transkrip.
5. **Peringatan khusus Windows**:
   - `torchcodec` gagal dimuat (DLL FFmpeg 7 tidak ketemu). WhisperX memberi audio yang sudah dimuat ke memori, jadi tidak mematikan proses, tetapi log penuh peringatan.
   - Cache Hugging Face memberi peringatan symlink (butuh Developer Mode agar hemat disk). Hanya peringatan, bukan galat.
6. **PyTorch terpasang versi CPU** (`2.8.0+cpu`). GPU RTX 4060 (8 GB) belum diuji.

## Alignment dan `process()` (diukur 18 Okt, klip 1 menit, model small)

- Tanpa alignment: 44,8 dtk, 3 segmen panjang, 1 pembicara.
- Dengan alignment (`cahya/wav2vec2-large-xlsr-indonesian`): sekitar 51 dtk total, 13 segmen per kalimat, 2 pembicara. Biayanya kecil, manfaatnya besar untuk label pembicara dan klik timestamp.
- Bug ditemukan dan diperbaiki: `transformers` menjalankan thread unduhan konversi safetensors (+1,2 GB) sehingga proses tidak keluar. Diatasi dengan `DISABLE_SAFETENSORS_CONVERSION=true` di `config.apply_hf_env()`.

### Tahap 1-4 lengkap dengan alignment, lewat `process()` (3 klip 5 menit, model small, CPU)

| Klip | Total | Tahap 2 (muat model + VAD) | Tahap 3 (teks + alignment) | Tahap 4 (pembicara) | Memori puncak | Segmen | Pembicara |
|---|---|---|---|---|---|---|---|
| uji-a | 178,5 dtk | 26,3 | 48,2 | 102,4 | 4,2 GB | 41 | 1 |
| uji-b | 182,0 dtk | 30,1 | 47,5 | 102,6 | 4,2 GB | 58 | 2 |
| uji-c | 172,2 dtk | 25,8 | 42,3 | 102,6 | 4,1 GB | 85 | 3 |

- Rasio sekitar 0,6 (waktu proses 0,6x durasi audio). Rekaman 1 jam diperkirakan 35-40 menit di CPU ini (ekstrapolasi, belum diukur).
- **Diarization adalah tahap paling lama** (~57% waktu), bukan transkripsi. Waktunya hampir sama di ketiga klip, jadi menyangkut durasi audio, bukan jumlah pembicara.
- Klip b: satu segmen 20 detik (detik 54-74) berisi kata "iya" berulang sekitar 90 kali. Hampir pasti halusinasi Whisper pada bagian hening atau derau. Perlu didengarkan manusia untuk memastikan.

### Tahap 5 (Gemini), diukur 18 Okt

- Kunci API valid. Model yang mendukung `generateContent` dicek langsung lewat `models.list()` di akun, bukan dari daftar pihak ketiga.
- Alur lengkap tahap 1-5 pada klip 5 menit: 192 dtk total, tahap 5 sekitar 10 dtk (satu panggilan). Tahap 5 tidak menambah beban berarti.
- Perbandingan pada transkrip klip c (85 segmen, 3 pembicara):

| Model | Waktu | Catatan |
|---|---|---|
| `gemini-3.1-flash-lite` | 6,0 dtk | **Mengarang pemilik tugas**: mengisi `owner` dengan "Peserta" dan "Panitia", padahal kedua kata itu tidak ada di transkrip. Melanggar aturan prompt. |
| `gemini-3.8-flash` | 6,7 dtk | Mengisi `owner` dengan `null` sesuai aturan. |

- Rekomendasi sementara: `LLM_MODEL=gemini-3.8-flash`. Ini hanya satu transkrip, jadi bukan kesimpulan akhir. Penilaian kualitas ringkasan pada 5 rekaman (22 Okt) tetap tugas PM.
- Untuk PM: prompt perlu menegaskan bahwa peran umum seperti "panitia" atau "peserta" bukan nama pemilik tugas, kecuali diucapkan.
- Belum diketahui apakah akun ini berada di paket gratis atau berbayar. Batas harian paket gratis akan terlihat sebagai galat `LLM_QUOTA`.

## Optimasi kecepatan (diukur 18 Okt, CPU i9-14900HX, klip c 5 menit, model small)

Tujuan: diarization memakan ±57% waktu. Hasil: **tidak ada parameter CPU yang layak dipakai; bawaan sudah paling baik.**

Isi diarization: embedding pembicara menghabiskan ±91% waktunya (segmentasi hanya ±9%).

| Percobaan | Hasil | Keputusan |
|---|---|---|
| `segmentation_step` 0,1 (bawaan) | 61,8 dtk, 3 pembicara | tetap |
| `segmentation_step` 0,2 | 31,5 dtk, **2 pembicara** (cocok baseline 66%) | ditolak |
| `segmentation_step` 0,3 / 0,5 | 21,4 / 12,7 dtk, 2 pembicara (cocok 42% / 41%) | ditolak |
| thread torch 24 (bawaan) / 16 / 12 / 8 | 61,4 / 65,9 / 71,9 / 71,9 dtk | tetap 24 |
| batch 32 (bawaan) / 64 / 8 | 61,8 / 61,3 / 79,8 dtk | tetap 32 |
| thread Whisper (`threads`) 4 (bawaan) / 8 | STT 32,7 / 36,4 dtk | tetap 4 |
| thread Whisper 16 | **proses mati mendadak** (kode keluar 127, 2 dari 2 percobaan) | hindari |
| diarization dan Whisper berjalan bersamaan | Whisper 69 dtk (sendiri 33), diarization 107 dtk (sendiri 61) | ditolak: berebut CPU, total lebih lama |

Catatan: `segmentation_step` di pyannote hanya dibaca saat objek dibuat. Mengubahnya setelah itu tidak berpengaruh kecuali `_segmentation.step` ikut diatur. Percobaan pertama saya salah karena itu (hasil tidak berubah), lalu diulang dengan benar.

**GPU (RTX 4060, 8 GB) belum bisa diukur.** Torch yang terpasang versi CPU. Versi CUDA (`torch 2.8.0+cu126`) berukuran 2,9 GB, dan unduhannya macet atau berjalan ±0,1 MB/s pada sesi ini (sempat 6 MB/s sesaat). Satu-satunya jalan nyata untuk mempercepat adalah GPU, karena embedding adalah perkalian matriks yang cocok untuk GPU. Belum ada angka, jadi belum ada klaim percepatan.

## Belum selesai

- Akurasi teks dan kebenaran label pembicara belum dinilai manusia. Angka di atas hanya jumlah pembicara dan kecepatan.
- Keputusan ukuran model akhir (`small` vs `medium`) menunggu penilaian kualitas.
