# Teyvat Archive

Dashboard Genshin Impact untuk melihat showcase karakter, build, dan ranking akun. Data showcase berasal dari Enka.Network, ranking dari Akasha, dan fitur akun pribadi menggunakan koneksi HoYoLAB opsional.

## Fitur

- Showcase karakter beserta senjata, artefak, dan statistik build.
- Ranking build melalui Akasha.
- Daily Notes dan progres eksplorasi melalui HoYoLAB.
- Pilihan bahasa, tema, dan akun.

## Menjalankan secara lokal

Gunakan Python 3.12.

```sh
python -m venv .venv
```

Aktifkan virtual environment:

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```sh
source .venv/bin/activate
```

Pasang dependensi dan jalankan aplikasi:

```sh
python -m pip install -r requirements.txt
python cli.py serve
```

Buka alamat yang ditampilkan di terminal. Masukkan UID Genshin untuk melihat showcase dan ranking. Koneksi HoYoLAB dapat diatur melalui halaman Settings untuk mengakses fitur akun pribadi.

## Sumber dan atribusi

- [Enka.Network](https://enka.network/) — data showcase.
- [Akasha System](https://akasha.cv/) — ranking build.
- [genshin.py](https://github.com/thesadru/genshin.py) — integrasi HoYoLAB.
- [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) — font dengan lisensi SIL Open Font License di `static/fonts/OFL.txt`.

Artwork Genshin Impact milik HoYoverse. Proyek ini merupakan proyek independen dan tidak berafiliasi dengan HoYoverse, Enka.Network, atau Akasha System.
