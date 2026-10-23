# Keputusan Cakupan MVP 1 setelah Uji Audio Besar

**Status:** usulan PM, 23 Okt 2026. **Belum diputuskan.** Keputusan akhir diambil PM bersama Dev 1 dan Dev 2.
**Tanggal keputusan yang diusulkan:** Rabu 28 Okt 2026 (sebelum M1, Jumat 30 Okt).

## 1. Fakta yang ada

Dari laporan uji audio besar Dev 1 (22 Okt) dan laporan kecepatan Dev 2 (18 Okt):

| Hal | Rekaman rapat nyata 27–42 menit | Klip uji 5 menit |
|---|---|---|
| Pembicara terdeteksi | 5, 6, dan 7 | 1, 2, dan 3 |
| Jalur teknis (unggah sampai hasil) | Berhasil 3 dari 3 | Berhasil |
| Mutu transkrip | **Rusak**: sekitar 15–18% kata adalah pengulangan tak diucapkan, sekitar 30% segmen hanya 1–2 kata, banyak salah dengar istilah | Belum dinilai manusia. Ada satu kasus pengulangan "iya" berulang |
| Label pembicara | Tidak bisa dibuktikan, satu label menguasai 48–58% waktu | Belum dinilai manusia |
| Ringkasan | Cukup baik, tetapi **menutupi** kerusakan transkrip (LLM menebak kata yang salah dengar) | Belum dinilai |
| Kecepatan | Sekitar 1,9 kali durasi (41 menit butuh 1 jam 19 menit) di laptop Dev 1 | Sekitar 0,6 kali di laptop Dev 2 |

Penyebab yang **terbukti**: kecepatan (CPU, rasio konsisten), pengulangan terjadi di ketiganya, dan gejala segmen identik berulang. Penyebab yang masih **dugaan**: pemicu pengulangan (suara tumpang tindih atau tawa), ukuran model sebagai sumber salah dengar, dan penyebab label pembicara kacau. Konfigurasi saat ini: Whisper `small`, CPU, `int8`.

Rekaman yang diuji adalah percakapan santai dengan banyak orang, bahasa campur, dan istilah teknis. Itu **lebih sulit** daripada yang diasumsikan di awal MVP 1.

## 2. Pertanyaan yang harus dijawab

Apakah MVP 1 harus mampu menangani **rapat panjang dengan banyak pembicara** pada kualitas yang bisa dipakai?

## 3. Pilihan

| | A. Pertahankan target, perbaiki pipeline | B. Persempit cakupan sekarang | C. **Ukur dulu, putuskan 28 Okt** (usulan) |
|---|---|---|---|
| Isi | Pakai model lebih besar dan tuning, target tetap rapat panjang banyak pembicara | Tulis batas jelas: rekaman lebih pendek, pembicara lebih sedikit, audio jernih. Perbaikan menjadi tahap berikutnya | Beri waktu 3–4 hari untuk mengukur dampak perbaikan pada klip 5 menit, lalu pilih A atau B berdasarkan angka |
| Keuntungan | Produk lebih dekat ke tujuan akhir | Jujur dan terjaga jadwalnya (6 Nov) | Keputusan berdasar data. Penyebab saat ini masih dugaan |
| Risiko | Perbaikan belum terbukti. Model besar lambat di CPU, GPU hanya ada di laptop tertentu. Jadwal bisa meleset | Mungkin dianggap terlalu sempit, dan tidak menjawab penyebab | Memakai 3–4 hari dari jadwal. Tanpa disiplin, menunda keputusan |

**Mengapa saya mengusulkan C:** laporan sendiri menyebut penyebab utama (model terlalu kecil, pemicu pengulangan) belum terbukti. Memilih A atau B sekarang berarti menebak. Pengukuran pada klip 5 menit murah, dan hasilnya langsung menentukan A atau B.

## 4. Rencana usulan C

| Tanggal | Siapa | Pekerjaan | Hasil yang diharapkan |
|---|---|---|---|
| Jum 23 – Sen 26 Okt | **PM** | Pilih 2 jendela per rekaman, tulis transkrip acuan, dengarkan titik masalah (lihat `docs/uji/panduan-transkrip-acuan.md`) | WER dasar untuk model `small`, akurasi label, jawaban 4 pertanyaan |
| Sen 26 – Rab 28 Okt | **Dev 2** | Bandingkan `medium` dan `large-v3` pada jendela yang sama (GPU di laptop yang punya), lalu tuning VAD dan penalti pengulangan (`transcribe.py`) | Waktu dan kualitas per konfigurasi |
| Sen 26 – Rab 28 Okt | **Dev 1** | Saring pengulangan untuk tampilan (data mentah tetap), peringatan "kualitas rendah", tombol unduh transkrip, uji pengisian jumlah pembicara | Tampilan lebih jujur dan lebih bersih |
| Rab 28 Okt | **PM + Dev** | Putuskan A atau B, tetapkan target WER, perbarui definisi selesai | Cakupan MVP 1 tertulis |

Semua tanggal adalah usulan. Dev 1 dan Dev 2 perlu menyatakan apakah beban ini muat.

## 5. Usulan sikap PM atas 9 usulan di laporan Dev 1 (belum disetujui)

| No | Usulan laporan | Sikap usulan | Catatan |
|---|---|---|---|
| 1 | Saring pengulangan di adapter API | **Setuju**, dengan syarat data mentah tidak dibuang | Aturan sudah ada di `kontrak-json.md` v1.1 (`repeat_count`) |
| 2 | Peringatan kualitas di halaman Hasil | **Setuju** | Kode `REPEATED_TEXT` dan `LOW_TRANSCRIPT_QUALITY` sudah diusulkan di kontrak v1.1 |
| 3 | Tombol unduh transkrip dan label "ringkasan memperbaiki salah dengar" | **Setuju**, prioritas rendah | Memudahkan penilaian PM |
| 4 | Isi jumlah pembicara saat unggah | **Setuju untuk diuji** | Belum terbukti memperbaiki |
| 5 | Bandingkan model `medium` atau `large-v3` | **Setuju, prioritas pertama** | Pada jendela yang sama dengan penilaian PM |
| 6 | Tuning VAD, penalti pengulangan, `initial_prompt` istilah rapat | **Setuju, prioritas kedua** | Menyentuh `transcribe.py`, keputusan Dev 2 |
| 7 | Pra-pemrosesan audio | **Tunda** | Belum ada bukti manfaat |
| 8 | Transkrip acuan 3–5 menit per rekaman | **PM mengerjakan** | Panduan sudah ada |
| 9 | Batas cakupan MVP 1 | **Dokumen ini** | Diputuskan 28 Okt |

Dua usulan tambahan:
- **Penyimpanan hasil sementara.** Pembatalan setelah 46 menit membuang semua hasil tahap 2–3. Usulan: simpan hasil tiap tahap (sudah ada untuk "Coba lagi") dan izinkan melanjutkan dari tahap terakhir yang selesai, bukan hanya dari yang gagal.
- **Perkiraan lama proses di layar Unggah.** Rasio 1,9× berarti rekaman 41 menit butuh 1 jam 19 menit. Tampilkan catatan itu sebelum pengguna menekan Proses. Ini tetap **perkiraan** dan bergantung pada laptop.

## 6. Definisi selesai MVP 1 (usulan revisi)

Kriteria lama hanya mengukur proses ("minimal 8 dari 10 rekaman selesai tanpa error"). Laporan 22 Okt menunjukkan itu tidak menangkap masalah mutu. Usulan kriteria baru:

| # | Kriteria | Cara mengukur |
|---|---|---|
| 1 | Minimal 8 dari 10 rekaman uji **dalam cakupan** selesai tanpa error | Seperti sebelumnya, tetapi hanya untuk rekaman yang masuk batas cakupan (bagian 7) |
| 2 | **Mutu transkrip** pada rekaman dalam cakupan mencapai target WER | Panduan transkrip acuan. **Target ditetapkan 28 Okt** setelah ada angka pertama |
| 3 | Pengulangan tak diucapkan **tidak tampil mentah** di halaman Hasil, dan rekaman dengan transkrip buruk mendapat peringatan kualitas | Uji manual pada 3 rekaman besar |
| 4 | Ringkasan tidak memuat fakta karangan pada transkrip uji prompt | `docs/uji/uji-prompt.md`: 0 karangan dari seluruh percobaan |
| 5 | Kedua laptop bisa menjalankan proyek hanya dengan README | Uji setup dari nol (4 Nov) |
| 6 | **Batas yang diakui** tertulis di README dan UI: lama proses, durasi, jumlah pembicara | Pemeriksaan dokumen dan layar |

## 7. Batas cakupan (diisi 28 Okt)

Contoh bentuknya, **angka belum ditetapkan** dan bergantung hasil ukur:

| Batas | Nilai |
|---|---|
| Durasi rekaman | ____ menit |
| Jumlah pembicara | sampai ____ |
| Bahasa | Indonesia, dengan istilah Inggris |
| Kondisi audio | Jernih, satu mikrofon jelas |
| Lama proses yang diterima | sampai ____ kali durasi |

## 8. Catatan dan keterbatasan

- Angka dalam dokumen ini diambil dari laporan Dev 1 dan Dev 2, bukan hasil ukur ulang saya. Penulis laporan menyatakan tidak mendengarkan audio, jadi tidak ada penilaian ketepatan kata atau pembicara dari mereka.
- Perkiraan 1 jam 55 menit untuk rekaman 1 jam adalah ekstrapolasi, bukan ukuran.
- Durasi pekerjaan pada rencana C adalah usulan awal, perlu ditinjau Dev 1 dan Dev 2.
- Dokumen ini tidak memuat isi rapat nyata. Rekaman dan transkripnya berisi nama dan informasi pihak lain, jadi jangan masukkan ke repo yang publik.
