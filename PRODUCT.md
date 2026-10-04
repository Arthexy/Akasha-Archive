# HoYo–Akasha Hub
<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
Pemain Genshin yang memeriksa showcase publik, build karakter, kategori ranking, dan rutinitas akun HoYoLAB sendiri. Dasar: PRD-Redesign-HoYo-Akasha-Hub.md; konteks diambil dari brief implementasi pengguna.

## Product Purpose
UID → showcase → detail build adalah jalur utama. Ranking dan catatan harian dapat diakses secara mandiri.

Explore World (/explore) menampilkan progres eksplorasi, level statue, reputasi/tribe, offering, dan detail area dari akun HoYoLAB terikat yang dipilih di Pengaturan. Pergantian akun membuang respons akun sebelumnya. Pilihan region tersimpan lokal per akun; total adalah rata-rata berbobot sama dari rata-rata region terpilih yang memiliki data. Map khusus tampil terpisah dan tetap masuk region terkait satu kali; nilai nol dipertahankan dan progres yang tidak tersedia tidak dibuat-buat.

## Capabilities and Constraints
FastAPI/Jinja2, JavaScript vanilla, CSS; tanpa dependency frontend baru. Enka menyediakan showcase publik, Akasha snapshot kategori, HoYoLAB notes privat akun terikat. Pertahankan null, nilai nol, TTL, CSRF, pembatasan host dan redaksi cookie. Tidak ada analytics atau data contoh pada mode pengguna.

## Evidence on Hand
README.md, PRD lama dan PRD redesign, models.py, endpoint dan test offline. Portrait berasal dari integrasi metadata yang sudah ada. Splash art baru bukan kebutuhan P0.

Artwork dan logo Explore World memakai sumber game resmi; asal aset lokal dicatat di static/images/explore/sources.json. Bukti pemeriksaan dan batas verifikasi visual berada di REDESIGN-QA.md.

## Accessibility & Inclusion
Keyboard, focus jelas, reduced motion, target sentuh 44 px dan reflow mobile. Klaim WCAG memerlukan verifikasi lebih lanjut.
