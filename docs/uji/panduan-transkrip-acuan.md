# Panduan Transkrip Acuan dan Penilaian Mutu

Dipakai PM untuk mengubah kesan "transkripnya rusak" menjadi **angka** yang bisa dibandingkan antar model dan antar pengaturan. Berkas ini sengaja **tidak memuat isi rapat nyata**, jadi aman di repo. Catatan yang memuat isi rapat taruh di `docs/uji/rekaman/` (diabaikan Git).

Latar: laporan uji audio besar (22 Okt) menyebut mutu belum bisa diukur karena tidak ada transkrip acuan. Empat hal yang hanya bisa dijawab dengan mendengarkan: jumlah pembicara sebenarnya, isi bagian yang diulang, apakah celah tanpa teks berisi ucapan, dan seberapa banyak kata salah dengar.

## 1. Pilih sampel

Untuk **tiap rekaman**, ambil dua jendela pendek:

| Jendela | Panjang | Dipilih dari | Tujuan |
|---|---|---|---|
| **Jernih** | 3 menit | Bagian yang jelas dan teratur | Batas atas: mutu terbaik yang bisa dicapai |
| **Ramai** | 2–3 menit | Bagian saling sela, tawa, atau banyak orang | Mutu pada kondisi sulit |

Catat jendela yang sama untuk semua pengujian ulang (model berbeda, pengaturan berbeda), supaya angkanya sebanding. Potong audionya dengan FFmpeg atau pemutar audio, dan simpan di `docs/uji/rekaman/`.

## 2. Tulis transkrip acuan

Dengarkan jendela itu dan tulis **apa yang benar-benar diucapkan**, apa adanya:
- Satu baris per giliran bicara, dengan waktu kira-kira dan **siapa yang bicara** (nama atau peran, bukan label SPEAKER).
- Tulis kata informal seperti diucapkan ("nggak", "gue"), jangan dibakukan.
- Istilah Inggris ditulis sebagaimana ejaan aslinya ("deploy", "VS Code").
- Bagian yang tidak terdengar jelas ditandai `[tidak jelas]` dan **tidak dihitung** dalam kata acuan.

Satu jendela 3 menit butuh sekitar 15–30 menit untuk ditulis dengan teliti (perkiraan saya). Mulai dari 2 jendela per rekaman, bukan semuanya sekaligus.

## 3. Hitung kesalahan kata (WER)

1. Samakan kedua teks: huruf kecil, tanpa tanda baca, angka ditulis dengan cara yang sama.
2. Bandingkan kata acuan dengan kata hasil pipeline pada jendela yang sama.
3. Hitung:
   - **S** (salah/ganti): kata ada tetapi salah. Contoh: "VS Code" menjadi "vscot".
   - **D** (hilang): ada di acuan, tidak ada di hasil.
   - **I** (tambahan): ada di hasil, tidak ada di acuan. **Kata hasil pengulangan tak diucapkan dihitung di sini.**
   - **N**: jumlah kata acuan.
4. **WER = (S + D + I) ÷ N**, dinyatakan dalam persen. Makin kecil makin baik. WER bisa lebih dari 100% bila banyak tambahan.

Cara cepat tanpa alat: ambil **100 kata acuan berturut-turut** dari jendela, cocokkan manual, dan hitung S, D, I. Cukup untuk perbandingan kasar.

| Rekaman | Jendela | Model | N | S | D | I | WER | Catatan |
|---|---|---|---|---|---|---|---|---|
| | jernih | | | | | | | |
| | ramai | | | | | | | |

Pisahkan juga **I yang berasal dari pengulangan** dari I lainnya. Dengan begitu terlihat berapa besar bagian WER yang bisa dihapus hanya dengan menyaring pengulangan, dan berapa yang butuh model lebih baik.

## 4. Nilai label pembicara

Pada jendela yang sama:

1. **Jumlah pembicara sebenarnya:** ______. Jumlah yang dideteksi pipeline: ______.
2. Petakan tiap label pipeline ke orang sebenarnya:

| Label pipeline | Orang sebenarnya | Catatan |
|---|---|---|
| SPEAKER_00 | | |
| SPEAKER_01 | | |

3. Periksa tiap segmen (atau 30 segmen pertama): apakah labelnya sesuai orang yang bicara?
   - **Akurasi label** = segmen dengan label benar ÷ segmen yang dinilai.
   - **Label terpecah:** satu orang mendapat lebih dari satu label.
   - **Label gabungan:** satu label dipakai beberapa orang.

| Rekaman | Jendela | Deteksi vs sebenarnya | Segmen dinilai | Benar | Akurasi | Terpecah? | Gabungan? |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 5. Nilai ringkasan

Untuk **tiap butir** di keputusan, tugas, dan pertanyaan terbuka, dengarkan bagian audionya, lalu isi:

| Butir | Didukung audio? (ya / sebagian / tidak) | Benar-benar disepakati? (untuk keputusan) | Pemilik benar? (untuk tugas) | Dikarang? | Dikoreksi LLM dari salah dengar, dan benar? | Catatan |
|---|---|---|---|---|---|---|
| | | | | | | |

Hal yang perlu dicurigai:
- Keputusan yang sebenarnya **hanya isi dokumen yang dibacakan atau didiskusikan**, bukan hal yang disepakati. Contoh: rapat yang membaca pasal kontrak bisa menghasilkan banyak "keputusan" yang sebenarnya isi pasal.
- Angka, nama, dan tanggal pada ringkasan. Cek satu per satu terhadap audio.
- Perbaikan kata oleh LLM ("cloud" menjadi nama produk): benar atau tebakan salah?

Skor ringkasan per rekaman (skala 1–5, sama dengan `hasil-uji.md`): 5 hampir tanpa salah; 4 salah kecil; 3 ada salah mengganggu; 2 banyak salah; 1 tidak bisa dipakai. Satu butir **dikarang** menurunkan skor setidaknya satu tingkat.

## 6. Jawab empat hal yang tidak diketahui

| Pertanyaan dari laporan 22 Okt | Cara menjawab | Hasil |
|---|---|---|
| Berapa pembicara sebenarnya di tiap rekaman? | Bagian 4, dengarkan beberapa bagian dari seluruh rekaman | |
| Apa isi sebenarnya di bagian yang diulang pipeline? | Dengarkan jendela yang dicatat laporan. Tulis apa yang diucapkan, dan apakah ada tawa, suara tumpang tindih, atau derau | |
| Apakah celah tanpa teks berisi ucapan? | Dengarkan celah itu. Isi: hening / ucapan hilang / derau | |
| Seberapa banyak kata salah dengar? | Bagian 3 (WER) | |

## 7. Target mutu

Jangan menetapkan target sebelum ada angka pertama. Setelah dua jendela per rekaman diukur dengan pengaturan saat ini (model `small`), tetapkan target di `docs/keputusan/cakupan-mvp1.md` bersama Dev 1 dan Dev 2. Sebagai titik awal diskusi saja (**bukan standar**, hanya perkiraan saya): untuk audio jernih dengan sedikit pembicara, WER di bawah sekitar 30% biasanya masih bisa dipakai untuk ringkasan, sedangkan di atas itu transkrip sulit dipercaya.
