# PRD redesign HoYo–Akasha Hub

Versi 1.0 · 1 Oktober 2026 · Status: spesifikasi usulan untuk desain dan implementasi

## 1. Keputusan dan konteks

Dokumen ini merancang ulang dashboard web HoYo–Akasha Hub yang sudah ada. Pengguna telah memilih scope redesign project ini. Arah visual, ukuran, dan target pengujian di bawah merupakan usulan PRD; belum menjadi desain yang disetujui atau hasil pengukuran.

Dasar produk berasal dari README.md, HoYo-Akasha-Hub-PRD.md, templates/dashboard.html, static/css/app.css, dan static/js/app.js. PRD lama tetap menjadi acuan integrasi, CLI, keamanan, dan layanan data. Dokumen ini menjadi acuan pengalaman web saat redesign diimplementasikan. Jika keduanya bertentangan, pertahankan kebenaran data dan keamanan, lalu catat keputusan sebelum mengubah perilaku.

Produk berjalan lokal dengan FastAPI, Jinja2, CSS, dan JavaScript vanilla. Dashboard menerima UID publik untuk membaca profil serta showcase melalui Enka.Network, ranking melalui Akasha, dan daily notes privat melalui koneksi HoYoLAB opsional.

Redesign harus membuat pemain cepat menemukan karakter, membaca build, memahami konteks ranking, dan mengecek kebutuhan harian. Artwork Genshin memberi identitas; angka, label, dan kontrol tetap mudah dibaca.

## 2. Masalah yang ingin diselesaikan

Pemeriksaan source menunjukkan seluruh UI memakai bahasa terminal: monospace, huruf kapital, penomoran section, bingkai kotak, dan label teknis seperti adapter atau config.json. Hierarkinya perlu diuji melalui render saat implementasi; dokumen ini belum mengklaim telah melakukan audit visual browser.

Detail karakter berada di bawah daftar showcase. Pengguna berpotensi kehilangan posisi daftar ketika membaca build panjang. Ranking membawa banyak kolom dan asumsi yang perlu terbaca bersama nilai rank. Daily notes juga harus selalu menunjukkan akun privat yang digunakan agar tidak tercampur dengan UID publik.

Masalah yang menjadi sasaran redesign:

- Identitas karakter kurang dominan dibanding chrome dashboard.
- Angka utama, informasi tambahan, dan metadata teknis membutuhkan tingkat penekanan yang berbeda.
- Perpindahan daftar ke detail perlu punya jalan kembali yang jelas.
- Kondisi data kosong, tidak lengkap, kedaluwarsa, dan gagal perlu menjelaskan langkah berikutnya.
- Form koneksi privat perlu membedakan menyimpan cookie, menguji koneksi, dan memilih akun.

## 3. Pengguna dan tugas utama

| Pengguna | Situasi | Tugas | Hasil yang dibutuhkan |
|---|---|---|---|
| Pemilik akun | Mengecek build setelah mengganti artifact | Memuat UID, memilih karakter, membaca stats dan artifact | Build terbaca beserta sumber dan waktu datanya |
| Pemain yang meninjau akun lain | Hanya punya UID publik | Membuka showcase dan ranking | Dapat memakai fitur publik tanpa koneksi HoYoLAB |
| Pemilik koneksi HoYoLAB | Mengecek rutinitas melalui HP | Membaca Resin, commissions, dan expeditions | Mengetahui kondisi akun privat yang dipilih |
| Pemain yang membaca ranking | Melihat posisi suatu build | Membuka kategori dan asumsi leaderboard | Memahami batas makna ranking |

Tugas utama adalah UID → showcase → detail karakter. Ranking dan daily notes merupakan tujuan lanjutan yang dapat dibuka langsung dari navigasi.

## 4. Tujuan dan ukuran keberhasilan

Target berikut dipakai untuk uji penerimaan, bukan klaim performa produk saat ini.

| Tujuan | Cara memeriksa | Target |
|---|---|---|
| Pengguna menemukan aksi awal | Uji tugas pada 5 pemain yang belum memakai dashboard | Minimal 4 menemukan input UID dan memulai pemuatan dalam 15 detik |
| Detail build mudah ditemukan | Tugas memilih karakter setelah showcase tersedia | Minimal 4 dari 5 membuka detail dalam 2 aksi setelah masuk Showcase |
| Ranking dipahami | Minta penguji menjelaskan satu row ranking | Minimal 4 menyebut kategori dan memahami snapshot bisa berbeda dari Enka |
| Akun privat jelas | Berikan skenario UID publik berbeda dari akun notes | Semua penguji dapat menunjuk UID yang dipakai notes |
| Mobile dapat dipakai | Uji pada lebar 360, 390, dan 768 px | Tidak ada scroll horizontal pada halaman utama |
| Kejujuran data terjaga | Fixture null, partial, stale, dan error | Tidak ada nilai hilang yang ditampilkan sebagai angka nol |

Pengujian memakai observasi lokal. Tidak menambahkan telemetry, analytics, atau penyimpanan UID eksternal untuk mengukur target ini.

## 5. Scope

### Wajib dalam redesign

- Shell, navigasi, input UID, dan feedback pemuatan akun.
- Overview, Showcase, detail karakter, Rankings, Daily notes, dan Settings.
- Sistem warna, tipografi, spacing, komponen, dan motion yang konsisten.
- Seluruh state penting, keyboard navigation, dan layout mobile.
- Pelestarian search, filter element, sort dua arah, pagination, detail kategori ranking, dan visibility toggle input cookie.
- Pemisahan akun publik dan privat serta freshness per sumber.

### Di luar scope

Login publik, cloud sync, social feed, berita patch, peta interaktif, damage calculator, artifact optimizer, tier list, team recommendation, AI assistant, gacha simulator, auto check-in, dan perubahan CLI.

Fitur tersebut membutuhkan data, aturan, atau layanan baru. Masukkan ke PRD terpisah ketika ada kebutuhan nyata. Redesign ini tidak menambah dependency frontend, database, framework baru, atau sistem tema per karakter.

## 6. Arah visual usulan

Nama kerja arah desain: **Arsip build Teyvat**. Dashboard memakai komposisi editorial gelap dengan portrait karakter yang jelas, ruang baca netral, angka tersusun rapi, dan aksen emas kusam. Bentuk emblem kecil serta pembatas halus memberi nuansa arsip petualangan tanpa membuat setiap kontrol terlihat seperti menu game.

First viewport sesudah akun dimuat memperlihatkan identitas pemain, waktu snapshot, akses ke showcase, dan preview karakter. Pengguna harus mengenali bahwa halaman membaca akun Genshin dari konten yang tampil.

Komposisi berubah mengikuti tugas. Showcase mengutamakan portrait dan pemilihan karakter; detail memakai dua kolom artwork dan data; ranking memakai tabel; notes memakai indikator resource. Jangan memaksakan grid kartu yang sama ke semua halaman.

### Palet awal

| Token | Nilai usulan | Penggunaan |
|---|---|---|
| Background | #101719 | Latar halaman |
| Surface | #182225 | Panel baca dan kontrol |
| Raised surface | #213034 | Dialog dan hover |
| Primary text | #F1EFE7 | Judul, angka, label utama |
| Secondary text | #B5C0BE | Deskripsi dan metadata |
| Border | #354447 | Pemisah dan batas input |
| Accent | #D8BB78 | CTA utama, pilihan aktif, detail identitas |
| Success | #9BCCAA | Keberhasilan dan koneksi aktif |
| Warning | #E5BC75 | Snapshot lama dan cooldown |
| Error | #F0A39C | Input atau request gagal |

Nilai ini adalah titik awal. Implementasi wajib mengukur kontras setiap kombinasi yang digunakan. Aksen element berasal dari identitas element dan dibatasi pada icon, label, atau garis kecil. Warna status memakai teks pendamping.

### Tipografi dan spacing

- Usulan judul: serif dengan bentuk tenang seperti Source Serif 4. Body dan kontrol: sans serif seperti Source Sans 3. Gunakan fallback sistem sampai file font dan lisensinya tersedia; font tidak menjadi dependency build.
- JetBrains Mono yang sudah ada dapat digunakan untuk UID. Angka stats memakai tabular numerals; seluruh kalimat tidak memakai monospace.
- Body desktop dan mobile 16 px dengan line-height sekitar 1.5. Metadata minimum 13 px. Judul halaman 32–40 px desktop dan 26–32 px mobile.
- Skala spacing 4, 8, 12, 16, 24, 32, 48 px. Jarak mengikuti kelompok informasi, bukan ditambahkan merata di semua elemen.
- Content width maksimum sekitar 1280 px. Padding 32 px desktop dan 16 px mobile. Ukuran akhir diuji dengan konten terpanjang.
- Radius panel 8 px, input 6 px, badge berbentuk pill hanya untuk status singkat. Shadow dipakai pada overlay, bukan setiap panel.

### Aturan anti-slop yang dapat diperiksa

| Pola yang ditolak | Pengganti yang diwajibkan |
|---|---|
| Hero pemasaran panjang di dashboard | Input UID atau data akun hadir di viewport awal |
| Gradient neon, glass panel, dan glow di seluruh UI | Permukaan netral dengan batas jelas; warna muncul ketika menjelaskan data |
| Semua section berupa kartu identik | Pilih tabel, daftar, indikator, atau artwork sesuai tugas |
| Artwork besar yang menutupi teks | Area gambar dan area baca punya batas; teks tetap terbaca ketika gambar gagal |
| Kartu di dalam kartu berlapis | Satu surface dengan subbagian dan divider |
| Statistik atau grafik dekoratif | Tampilkan hanya nilai dan visual yang memiliki data serta pertanyaan pengguna |
| Label seperti “Ultimate”, “Powerful”, “Unlock your potential” | Label tindakan atau objek: “Muat akun”, “Detail build”, “Perbarui ranking” |
| Warna rarity atau rank sebagai satu-satunya arti | Nama, angka, dan label tersedia bersama warna |
| Setiap hover mengangkat atau memperbesar kartu | Hover menandai target; layout dan ukuran tetap stabil |
| Animasi beruntun yang menunda konten | Konten tampil segera; animasi kecil menjelaskan perubahan state |
| Angka, nama, atau ranking buatan pada halaman pengguna | Empty state nyata; data contoh hanya di fixture berlabel |

## 7. Struktur informasi dan navigasi

| Tujuan | Label UI | Fungsi |
|---|---|---|
| Overview | Ringkasan | Identitas akun, preview showcase, ringkasan resource |
| Showcase | Showcase | Search, filter, sort, daftar karakter |
| Detail | Detail build | Stats, weapon, talents, artifact, konteks ranking |
| Rankings | Ranking | Posisi per kategori dan asumsi leaderboard |
| Notes | Catatan harian | Resource dari akun HoYoLAB yang dipilih |
| Settings | Pengaturan | UID default, opsi sumber, koneksi, pemilihan akun |

Usulan bahasa utama adalah Indonesia. Istilah game dan nama karakter/item mengikuti metadata sumber agar tetap dikenali. Dukungan bahasa lain belum masuk scope.

Desktop memakai sidebar ringkas sekitar 224 px. Topbar menunjukkan akun publik aktif dan aksi refresh yang relevan. Settings mudah ditemukan di bawah navigasi utama. Jam lokal dan label versi tidak mengalahkan informasi akun.

Mobile memakai header ringkas dengan tombol menu berlabel “Navigasi”. Menu menjadi drawer berisi seluruh tujuan; tidak menjejalkan enam tujuan ke bottom bar. Drawer menutup setelah tujuan dipilih, menangani Escape, dan mengembalikan focus ke pemicu.

Pertahankan pendekatan single dashboard bila mencukupi. Gunakan hash untuk tujuan dan detail bila ingin mendukung Back/Forward tanpa menambah router library. Jangan masukkan cookie ke URL. UID di URL hanya ditambahkan jika perilakunya sengaja dipilih saat implementasi.

## 8. Spesifikasi halaman

### 8.1 Sebelum akun dimuat

Judul “Lihat showcase akun Genshin” diikuti input UID dan tombol “Muat akun”. Teks bantuan: “Gunakan UID publik. Showcase dapat dibuka tanpa koneksi HoYoLAB.” Sediakan penjelasan singkat cara mengaktifkan detail showcase di game.

Jangan tampilkan rangkaian kartu berisi tanda kosong sebelum pengguna melakukan apa pun. Akun privat yang sudah terhubung tetap dapat membuka notes tanpa menunggu UID publik.

### 8.2 Ringkasan

Urutan baca: identitas pemain → status snapshot → preview showcase → ringkasan notes jika aktif → status sumber sekunder.

- Profil memuat avatar, nickname, UID yang dapat disalin, dan field profil yang tersedia.
- UID panjang tidak terpotong sehingga sulit diverifikasi. Aksi salin memberi feedback “UID disalin”; kegagalan clipboard menyediakan teks yang dapat dipilih.
- Preview memakai maksimal 4 karakter dan aksi “Lihat semua karakter”. Tidak memilih “karakter terbaik” tanpa aturan atau data pendukung.
- Ringkasan notes menampilkan identitas akun privat, Resin, dan satu akses ke notes lengkap.
- Ketika HoYoLAB belum terhubung, tampilkan satu ajakan ringkas dengan tautan Pengaturan.
- Status Enka, Akasha, dan HoYoLAB berada dalam baris sekunder yang bisa diperluas, dengan timestamp masing-masing.

### 8.3 Showcase

Header berisi jumlah hasil, search nama, filter element, sort nama/level, dan arah sort. Search/filter berjalan pada showcase yang tersedia dan tidak menjanjikan seluruh inventory.

Desktop memakai grid portrait dengan 3–4 kolom sesuai ruang konten. Pada 360–390 px gunakan 2 kolom jika nama dan tombol tetap nyaman; jika tidak, turunkan ke satu kolom. Setiap item menunjukkan portrait, nama, element dengan label, level, constellation bila tersedia, dan aksi “Lihat build”.

Portrait menjadi target visual utama. Identitas tidak bergantung pada gambar karena nama selalu tampil. Jika karakter terlihat tanpa detail build, item menjelaskan “Detail build belum dipublikasikan” dan menyediakan konteks, tanpa memberi tombol yang berakhir kosong.

Filter memunculkan chip pilihan aktif dan tombol “Hapus filter”. Jumlah hasil berubah setelah filter diterapkan. Pagination memakai 10 item per halaman sesuai pola yang sudah ada, dengan Previous/Next dan posisi halaman. Perubahan search, filter, atau sort kembali ke halaman pertama.

### 8.4 Detail build

Detail menjadi tujuan tersendiri dalam dashboard. Tombol “Kembali ke showcase” mengembalikan filter, halaman, dan posisi scroll. Fokus kembali ke karakter yang dibuka.

Desktop: portrait pada sekitar sepertiga lebar, ringkasan build pada sisanya. Mobile: nama dan identitas → ringkasan stats → weapon → talents → artifact → ranking. Artwork mobile diperkecil agar stats pertama dapat muncul tanpa melewati poster panjang.

Isi wajib:

1. Nama, element, level, constellation, portrait, serta timestamp snapshot Enka.
2. Ringkasan HP, ATK, DEF, Elemental Mastery, CRIT Rate, CRIT DMG, dan Energy Recharge apabila tersedia. Bonus damage memakai label element yang sesuai data.
3. Stats tambahan dalam disclosure “Semua statistik”. Nilai dari provider tetap dibedakan dari nilai turunan lokal.
4. Weapon: nama, gambar bila tersedia, level, refinement, rarity, dan stats tersedia.
5. Talents: nama/label yang dapat dipahami; bila metadata tidak tersedia, gunakan label fungsional dan level yang ada tanpa mengarang modifier.
6. Artifact menurut slot: nama, set, level, rarity, main stat, seluruh substats, dan CV.
7. Ranking terkait karakter beserta kategori dan label bahwa kecocokan build belum diverifikasi.

Setiap artifact ditampilkan sebagai satu blok datar. Substats tersusun dalam baris label/nilai, bukan kalimat berantai. Penekanan CRIT boleh membantu scan, tetapi tidak memberi penilaian “bagus” atau “buruk”. CV dijelaskan sebagai 2 × CRIT Rate + CRIT DMG dari substats artifact saja; main stat dan weapon tidak dihitung.

### 8.5 Ranking

Desktop memakai tabel dengan kolom karakter, kategori, rank/populasi, Top %, weapon/asumsi ringkas, CV, dan set bila tersedia. Informasi level boleh ditempatkan dekat identitas karakter untuk mengurangi lebar tabel.

Angka rata kanan. Kategori memakai tombol yang membuka detail penuh. Sort memiliki indikator arah dan aria-sort yang sesuai. Nilai unavailable tidak menjadi angka nol atau peringkat pertama ketika diurutkan; letakkan setelah nilai tersedia di kedua arah sort.

Mobile memakai daftar row yang memperlihatkan karakter, kategori, rank/populasi, dan Top % terlebih dahulu. Detail tambahan dibuka melalui “Asumsi kategori”. Seluruh kolom tetap dapat diakses melalui detail; tidak disembunyikan permanen demi layout.

Dialog menampilkan kategori lengkap, weapon asumsi, bracket, detail dari sumber, rank, populasi, set, timestamp, dan peringatan “Snapshot Akasha bisa berbeda dari showcase Enka. Kecocokan build belum diverifikasi.”

Top % ditampilkan dengan aturan pembulatan konsisten. Jika pembulatan akan membuat nilai positif tampak 0%, gunakan presisi tambahan atau label batas yang benar. Ranking adalah per kategori; tidak digabung menjadi skor akun atau tier buatan.

### 8.6 Catatan harian

Bagian paling atas menunjukkan nickname/UID akun HoYoLAB yang dipilih dan waktu terakhir diperbarui. Jika berbeda dari akun publik, tampilkan “Catatan harian menggunakan akun HoYoLAB ini” dekat identitasnya.

Resin menjadi nilai paling menonjol, dengan angka saat ini/maksimum dan perkiraan penuh bila data mendukung. Progress memakai maksimum dari sumber; tidak mengasumsikan kapasitas tetap.

Commissions memisahkan progress, klaim, serta Encounter Points sesuai model yang ada. Expeditions berupa daftar karakter dan waktu selesai. Realm currency, weekly discounts, dan transformer muncul jika didukung respons sumber.

Countdown berjalan lokal, disertai waktu pembaruan data. Jangan memberi label “live” untuk snapshot. Auto-refresh hanya aktif ketika tab terlihat, integrasi aktif, dan cooldown memungkinkan. Nilai unavailable tampil “Belum tersedia” tanpa progress bar kosong yang menyerupai nol.

### 8.7 Pengaturan

Bagi menjadi Preferensi, Koneksi HoYoLAB, dan Akun catatan harian. Setiap kelompok memiliki aksi simpan sendiri bila backend sudah mendukungnya; status tersimpan mengikuti respons server.

Alur koneksi: masukkan region dan cookie → simpan → uji koneksi → pilih akun terikat → aktifkan notes. Tampilkan tahap aktif dan apa yang belum selesai. Menyimpan cookie belum berarti koneksi berhasil.

Nama teknis cookie dipertahankan sebagai label field karena pengguna perlu memasukkan nilai yang tepat. Cookie tambahan berada dalam disclosure. Field password hanya memperlihatkan nilai yang baru diketik ketika visibility toggle diaktifkan; nilai tersimpan tidak dimuat kembali.

Teks penyimpanan harus akurat: “Cookie disimpan dalam config.json lokal sebagai teks biasa. Nilai tersimpan tidak dikirim kembali ke browser.” Jangan menyebut penyimpanan terenkripsi.

Aksi “Hapus kredensial” membuka konfirmasi yang menjelaskan koneksi dan notes akan dinonaktifkan. Setelah berhasil, tampilkan hasil server. Jika environment override masih ada, jelaskan bahwa pengguna perlu menghapusnya terpisah. Jangan mengklaim seluruh kredensial telah terhapus bila hanya file yang berubah.

Accent amber/green lama harus tetap ditangani dengan migrasi atau pemetaan yang terdokumentasi. Usulan visual baru tidak membenarkan menghapus preferensi tersimpan tanpa keputusan.

## 9. Perilaku lintas halaman

- Memuat UID baru mempertahankan inputnya selama request, tetapi tidak memberi label UID baru pada data akun lama.
- Setelah validasi, hasil akun lama dihapus atau ditampilkan dalam state transisi dengan identitas lamanya tetap jelas. Respons request UID sebelumnya yang datang terlambat tidak boleh menimpa akun aktif.
- Enka dan Akasha memiliki loading/error masing-masing. Hasil Enka tetap dapat dibaca ketika Akasha gagal.
- Tombol refresh hanya berlaku pada sumber yang dinyatakan labelnya. Refresh ditahan selama request aktif dan cooldown.
- Search, filter, sort, dan pagination tidak memicu request provider baru bila dataset yang dibutuhkan sudah tersedia.
- Focus, pilihan karakter, dan posisi scroll tidak hilang setelah pembaruan dataset kecuali objek tersebut memang tidak tersedia lagi.
- Jumlah item berbeda setelah refresh tidak boleh meninggalkan pengguna pada halaman pagination kosong.

## 10. State dan microcopy

| State | Tampilan | Aksi atau recovery |
|---|---|---|
| UID belum diisi | Form dan bantuan pendek | “Muat akun” |
| UID salah format | Error di bawah field; input tetap ada | “Masukkan UID dengan 9–10 digit angka.” Sesuaikan bila validator backend berubah |
| Request pertama berlangsung | Skeleton mengikuti bentuk konten; status tekstual | “Memuat showcase…” |
| Refresh berlangsung | Pertahankan snapshot dengan timestamp; indikator kecil | “Memperbarui data…” |
| Showcase kosong | Penjelasan tanpa contoh karakter palsu | “Belum ada karakter yang dipublikasikan di showcase.” |
| Filter tanpa hasil | Jumlah hasil nol dan filter aktif | “Tidak ada karakter yang cocok.” + “Hapus filter” |
| Detail karakter tidak publik | Identitas tetap terlihat | “Aktifkan detail karakter di showcase dalam game.” |
| Ranking tidak tersedia | Penjelasan dalam area ranking | “Ranking untuk akun ini belum tersedia.” |
| Provider gagal, cache ada | Data lama dengan banner dan waktu snapshot | “Menampilkan snapshot sebelumnya. Akasha belum dapat dihubungi.” |
| Provider gagal, cache tidak ada | Error hanya pada sumber terkait | “Coba lagi” ketika cooldown memungkinkan |
| Rate limit | Waktu tunggu dan tombol disabled | “Dapat diperbarui lagi dalam …” |
| HoYoLAB belum terhubung | Penjelasan satu paragraf | “Buka pengaturan koneksi” |
| Cookie kedaluwarsa | Status koneksi gagal tanpa stale notes privat | “Perbarui cookie lalu uji koneksi.” |
| Verifikasi dibutuhkan | Penjelasan dari error yang telah dinormalisasi | Buka situs/aplikasi resmi melalui tautan yang telah diverifikasi |
| Gambar gagal | Placeholder netral dengan nama tetap ada | Tidak mengulang request tanpa batas |
| Metadata hilang | Label fallback deskriptif; ID hanya sebagai bantuan | UI tetap dapat digunakan |

Toast dipakai untuk feedback singkat seperti salin atau simpan. Error yang memerlukan tindakan tetap berada dekat objek yang gagal. Jangan menyampaikan kegagalan koneksi hanya lewat toast yang hilang.

## 11. Motion dan interaksi

Transisi warna/border sekitar 120–180 ms. Detail atau dialog dapat memakai fade kecil sekitar 180 ms. Animasi tidak mengubah posisi angka saat membaca dan tidak menunda konten menunggu entrance selesai.

Tidak memakai parallax, cursor khusus, scroll hijacking, autoplay audio/video, atau particle background. Signature interaction usulan adalah perpindahan portrait dari daftar ke detail memakai View Transitions jika didukung, dengan fallback langsung. Efek ini P1; fungsi detail tetap P0.

Ketika prefers-reduced-motion aktif, hilangkan transform dan perpindahan gambar. Skeleton tidak berkedip cepat. Hover, focus, selected, loading, dan disabled memiliki tampilan berbeda serta tidak mengandalkan opacity rendah yang membuat teks tak terbaca.

## 12. Aksesibilitas dan responsivitas

Target penerimaan aksesibilitas: WCAG 2.2 AA untuk flow dalam scope. Klaim kepatuhan baru dibuat setelah pengujian yang sesuai; pemeriksaan otomatis saja tidak cukup.

- Kontras body minimal 4.5:1; teks besar dan batas kontrol bermakna minimal 3:1 sesuai konteksnya.
- Semua kontrol dapat digunakan lewat keyboard, focus terlihat, dan urutan tab mengikuti urutan baca.
- Target sentuh utama minimal 44 × 44 CSS px; aksi berdekatan memiliki ruang yang cukup.
- Dialog memiliki nama, focus trap, Escape, dan pengembalian focus. Drawer mengikuti pola yang sama ketika modal.
- Input memakai label permanen; placeholder bukan satu-satunya petunjuk. Error terhubung melalui aria-describedby.
- Status async memakai live region yang tepat. Countdown setiap detik tidak diumumkan terus-menerus oleh screen reader.
- Tabel desktop mempertahankan header semantik. Versi mobile menyediakan label data setara.
- Gambar dekoratif memiliki alt kosong; gambar identitas memakai alt yang tidak menduplikasi label secara berlebihan.
- Pada zoom 200%, tombol, input, dialog, dan data tidak terpotong. Pada lebar 320 CSS px, konten utama tetap reflow; tabel hanya boleh scroll di wrapper lokal jika diperlukan.

Breakpoint dipilih ketika konten tidak lagi muat, dengan 768 dan 1100 px sebagai titik awal pengujian. Desktop kecil tidak dipaksa memakai sidebar dan tabel dengan ukuran desktop lebar. Uji nickname panjang, kategori panjang, lima artifact, nama item multikata, serta nilai angka besar.

## 13. Kontrak data, aset, dan keamanan

| Informasi | Sumber | Aturan |
|---|---|---|
| Profil, karakter, weapon, artifact | Enka dan metadata yang sudah digunakan | Label sebagai snapshot showcase publik |
| Ranking dan asumsi | Akasha | Kategori dan timestamp tidak boleh hilang |
| Daily resources | Akun HoYoLAB terikat | Identitas privat terpisah dari UID publik |
| CV artifact | Perhitungan lokal yang ada | Jelaskan rumus dan basis substats |
| Waktu/cooldown | Service/provider dan timer lokal | Jangan mengganti TTL sumber dengan angka UI buatan |

Pertahankan null sebagai unavailable, nilai zero yang valid sebagai 0, dan precision sesuai jenis stat. Nama, signature, dan metadata provider adalah input tidak tepercaya; escape sebelum dirender. Jangan menambahkan HTML mentah dari sumber.

Gunakan portrait, icon weapon/artifact, dan metadata yang sudah didukung project. Artwork splash baru bersifat opsional dan baru dipakai setelah URL, asal, izin penggunaan, ukuran, serta fallback diperiksa. Jangan membuat AI art yang menyamar sebagai artwork resmi atau menempelkan logo HoYoverse seolah produk resmi.

Daftar aset implementasi harus mencatat sumber, peran, ukuran, attribution bila diperlukan, dan fallback. Jika hanya portrait kecil tersedia, desain tetap memakai portrait tersebut dengan skala wajar. Tidak memperbesar gambar rendah resolusi menjadi hero.

Pertahankan same-origin check, CSRF token, redaksi cookie, bound-account verification, dan pembatasan host yang sudah ada. Cookie tidak boleh masuk localStorage, query string, screenshot contoh, log, atau respons API. Dashboard tetap merupakan utilitas lokal; hosting publik memerlukan scope keamanan baru.

## 14. Performa dan pendekatan implementasi

Gunakan FastAPI/Jinja2, CSS, dan JavaScript vanilla yang sudah ada. Utamakan CSS Grid/Flexbox, dialog native, disclosure native, dan event handler sederhana. Jangan menambah React, animation library, router, icon package, atau state manager hanya untuk redesign.

Pisahkan render sesuai view di struktur yang sudah ada. Ekstrak helper ketika pola benar-benar berulang; jangan membuat component framework internal. Pertahankan service layer, adapter, cache, endpoint, dan batas TTL yang ada kecuali bug nyata mengharuskan perbaikan.

Target anggaran awal:

- HTML awal tidak menunggu provider selesai.
- CSS dan JavaScript inti gabungan maksimal 150 KB transfer terkompresi, font dan artwork dihitung terpisah.
- Artwork utama diusahakan maksimal 250 KB per gambar; thumbnail jauh lebih kecil sesuai ukuran tampil.
- Gambar di bawah fold memakai lazy loading; gambar utama yang terlihat segera tidak ditunda.
- Width/height atau aspect-ratio gambar ditetapkan untuk menghindari layout shift.
- Tidak menambah polling baru; request bersamaan untuk sumber/UID sama tetap dideduplikasi.

Target uji shell: LCP ≤2.5 detik dan CLS ≤0.1 pada skenario cold load lokal yang dicatat. Ukur respons interaksi pada search, membuka detail, dan pagination dengan target ≤200 ms. Waktu provider dilaporkan terpisah. Ini target laboratorium untuk redesign; status Core Web Vitals lapangan tidak dapat disimpulkan dari satu run lokal.

## 15. Prioritas dan urutan implementasi

| Tahap | Hasil | Syarat lanjut |
|---|---|---|
| 1. Konfirmasi arah | Desktop/mobile wireframe untuk entry, showcase, detail, ranking, notes, settings | Flow, identitas akun, dan prioritas baca disetujui |
| 2. Sistem dasar | Token, typography, shell, form, status, dialog | Keyboard dan reflow dasar bekerja |
| 3. Showcase dan detail | Jalur UID → karakter → artifact lengkap | Data dan state tidak mengalami regresi |
| 4. Ranking | Tabel, mobile rows, sort, pagination, dialog asumsi | Konteks kategori tersedia di semua viewport |
| 5. Notes dan settings | Resource, koneksi, pemilihan akun, hapus kredensial | Akun privat dan status autentikasi jelas |
| 6. Verifikasi | Screenshot, uji flow, pengukuran, perbaikan material | Acceptance criteria P0 lulus |

P0 mencakup fungsi, state, kejujuran data, keamanan, accessibility, dan responsive layout. P1 mencakup View Transitions serta splash art resolusi tinggi yang tersedia secara sah. Rilis P0 tidak bergantung pada P1.

## 16. Acceptance criteria

| ID | Skenario | Hasil yang wajib |
|---|---|---|
| AC-01 | Pengguna baru membuka dashboard | Input UID dan aksi utama terlihat tanpa scroll di viewport 390 × 844 dan 1440 × 900 |
| AC-02 | UID valid, HoYoLAB tidak terhubung | Profil, showcase, dan ranking yang tersedia tetap dapat digunakan |
| AC-03 | Enka berhasil, Akasha gagal | Showcase tetap tampil; area ranking menjelaskan kegagalan sendiri |
| AC-04 | Pengguna mencari/filter/sort | Hasil sesuai pilihan, jumlah benar, halaman kembali ke awal |
| AC-05 | Karakter dibuka lalu kembali | Filter, halaman, scroll, dan focus daftar dipulihkan |
| AC-06 | Build lengkap tersedia | Stats, weapon, talents, dan setiap artifact terbaca dengan nilai sumber yang sama |
| AC-07 | Field null dan zero disediakan fixture | Null menjadi unavailable; zero tetap 0 |
| AC-08 | Kategori ranking dibuka | Asumsi, weapon, rank/populasi, dan status kecocokan build tersedia |
| AC-09 | UID publik berbeda dari akun notes | Masing-masing view menunjukkan identitas yang benar |
| AC-10 | Cookie disimpan dan halaman dimuat ulang | Cookie tersimpan tidak tampil di field, source HTML, atau respons API |
| AC-11 | Cookie kedaluwarsa | Notes menampilkan status autentikasi gagal tanpa stale fallback privat |
| AC-12 | Cooldown aktif | UI menyebut waktu tunggu dan tidak mengirim retry dari klik berulang |
| AC-13 | UID A lalu UID B dimuat cepat | Respons A tidak menimpa B dan identitas/data tidak tercampur |
| AC-14 | Gambar atau metadata gagal | Nama/fallback, data, dan tindakan tetap dapat digunakan |
| AC-15 | Mobile, zoom, dan konten panjang | Tidak ada overflow halaman atau kontrol terpotong |
| AC-16 | Keyboard dan reduced motion | Semua flow selesai; dialog/drawer mengelola focus; motion mengikuti preferensi |
| AC-17 | Snapshot stale ditampilkan | Sumber dan waktu snapshot terlihat serta peringatan dekat data |
| AC-18 | Refresh mengurangi jumlah halaman | Pagination berpindah ke halaman valid dan tidak menampilkan page kosong |
| AC-19 | Koneksi disimpan tetapi belum diuji | UI tidak menampilkan status berhasil terhubung |
| AC-20 | Respons notes datang saat akun privat berubah | Data hanya dipasang jika masih cocok dengan akun aktif |

## 17. Pengujian dan definition of done

Gunakan test offline yang sudah ada untuk memastikan kontrak API, cache, bound account, CSRF, dan redaksi cookie tetap bekerja. Tambahkan test hanya untuk perilaku baru atau risiko regresi yang relevan. Verifikasi provider live tetap opt-in dengan akun penguji; jangan memakai kredensial contoh di repository.

Uji manual mencakup cold entry, public-only, build lengkap/tidak lengkap, partial provider failure, stale cache, cooldown, ranking kosong, cookie kedaluwarsa, beberapa akun privat, UID berubah cepat, dan gambar gagal. Uji keyboard serta screen reader setidaknya pada flow UID, detail, dialog kategori, dan pengaturan koneksi.

Ambil screenshot pada 360, 390, 768, 1280, dan 1440 px dengan konten nyata atau fixture berlabel. Periksa satu batch, perbaiki temuan material, lalu satu batch konfirmasi. Jangan menyatakan kualitas visual hanya berdasarkan source CSS.

Redesign selesai ketika seluruh AC P0 lulus, fitur lama dalam scope tetap tersedia, target yang belum tercapai dicatat, screenshot sesuai konten yang diuji, tidak ada secret dalam artefak, dan PRD/README diperbarui untuk perilaku yang benar-benar berubah. Tidak ada data contoh yang tersisa pada mode pengguna.

## 18. Keputusan yang masih terbuka

Scope dashboard telah dikonfirmasi. Sebelum implementasi visual, konfirmasikan arah “Arsip build Teyvat”, bahasa UI Indonesia, pilihan font/aset yang tersedia, dan pemetaan preferensi accent lama. Dokumen ini sengaja tidak menetapkan desain tersebut sebagai persetujuan pengguna.

Langkah desain pertama adalah membuat wireframe entry, showcase, dan detail build dengan fixture yang sama pada desktop serta mobile. Wireframe harus memperlihatkan identitas akun, timestamp, kontrol filter, setiap slot artifact, dan jalan kembali ke daftar sebelum masuk ke visual final.
