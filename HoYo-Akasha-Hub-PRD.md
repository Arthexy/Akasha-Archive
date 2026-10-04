# PRD — HoYo-Akasha Hub

**Versi:** 1.0  
**Jenis aplikasi:** Utilitas lokal dengan CLI dan Web Dashboard  
**Stack utama:** Python, FastAPI, Rich, Jinja2  
**Target MVP:** Genshin Impact  
**Ekstensi berikutnya:** Honkai: Star Rail, sesuai dukungan API

---

## 1. Ringkasan Produk

HoYo-Akasha Hub menyatukan dua kategori data dalam satu workspace lokal:

1. **Data publik akun dan karakter** dari Enka.Network serta Akasha System, diakses menggunakan UID tanpa login.
2. **Daily notes privat** dari HoYoLAB, diakses menggunakan cookie autentikasi opsional.

Pengguna dapat mengakses data melalui:

- **CLI**, untuk pemeriksaan cepat melalui terminal.
- **Web Dashboard**, untuk membaca statistik, artifact, ranking, dan status harian secara lebih terstruktur.

Kedua antarmuka memakai lapisan layanan, validasi, dan cache yang sama.

**Prinsip utama:** fitur publik harus tetap berfungsi meskipun pengguna tidak menghubungkan HoYoLAB.

## 2. Tujuan Produk

### 2.1 Tujuan utama

- Menampilkan showcase karakter berdasarkan UID.
- Menampilkan statistik dan artifact karakter secara terbaca.
- Menampilkan ranking Akasha apabila tersedia.
- Menampilkan status harian melalui HoYoLAB.
- Menyediakan pengalaman yang konsisten antara CLI dan dashboard.
- Berjalan lokal dengan dependency dan penggunaan resource minimal.
- Membuat perbedaan antara data publik, snapshot, dan data terautentikasi terlihat jelas.

### 2.2 Di luar cakupan MVP

- Login menggunakan username dan password HoYoverse.
- Mengambil cookie secara otomatis dari browser.
- Daily check-in otomatis.
- Otomasi gameplay.
- Kalkulator damage atau artifact optimizer.
- Sinkronisasi cloud dan multi-user.
- Hosting publik.
- Dukungan penuh seluruh game HoYoverse.
- Integrasi AI, Telegram, atau WhatsApp.

## 3. Pengguna dan Skenario Utama

### Persona A — Pengguna terminal

Ingin melihat status akun tanpa membuka dashboard.

> “Tampilkan Resin dan expedition lewat satu command.”

### Persona B — Pemantau build karakter

Ingin meninjau showcase, artifact, dan ranking build.

> “Masukkan UID lalu lihat karakter publik dan ranking yang tersedia.”

### Persona C — Pengguna privacy-first

Hanya membutuhkan data publik dan tidak ingin menyimpan cookie.

> “Aplikasi tetap berguna tanpa autentikasi HoYoLAB.”

## 4. Batasan dan Karakteristik Sumber Data

| Sumber | Autentikasi | Data utama | Batasan |
|---|---|---|---|
| Enka.Network | UID publik | Profil, showcase, stats, weapon, artifact | Bergantung pada showcase yang dipublikasikan; bukan seluruh inventory akun |
| Akasha System | UID publik | Ranking dan informasi leaderboard yang tersedia | Tidak setiap akun, karakter, atau build memiliki ranking |
| HoYoLAB | Cookie akun | Resin, commissions, expeditions, daily notes lain yang didukung | Cookie dapat kedaluwarsa; verifikasi atau pengaturan akun dapat menghalangi akses |

### Ketentuan penting

- Data Enka merupakan **snapshot showcase**, bukan live inventory.
- Ranking Akasha terkait **kategori leaderboard dan asumsi build tertentu**, bukan penilaian absolut semua karakter.
- UID publik yang sedang dilihat bisa berbeda dengan UID akun HoYoLAB.
- Autentikasi HoYoLAB tidak memberikan akses daily notes privat milik UID sembarang.
- `ltuid_v2` dan `ltoken_v2` merupakan input autentikasi awal. Kecukupannya perlu diverifikasi terhadap region dan endpoint; provider dapat membutuhkan cookie tambahan.
- DS signature bukan pengganti cookie dan tidak melewati CAPTCHA atau verifikasi akun.

## 5. Ruang Lingkup MVP

| ID | Fitur | Prioritas |
|---|---|---|
| F-01 | Konfigurasi UID lokal | P0 |
| F-02 | Validasi dan pemuatan konfigurasi | P0 |
| F-03 | Profil dan showcase Enka | P0 |
| F-04 | Detail stats, weapon, dan artifact | P0 |
| F-05 | Ranking Akasha jika tersedia | P0 |
| F-06 | Cookie HoYoLAB opsional | P0 |
| F-07 | Daily notes Genshin | P0 |
| F-08 | CLI berbasis Rich | P0 |
| F-09 | Dashboard FastAPI | P0 |
| F-10 | Cache, timestamp, dan penanganan error | P0 |
| F-11 | Masking dan redaksi cookie | P0 |
| F-12 | Dukungan beberapa game | P1 |
| F-13 | Beberapa profil akun lokal | P1 |
| F-14 | Ringkasan perubahan snapshot build | P2 |

**P0:** wajib untuk MVP.  
**P1:** pengembangan sesudah MVP.  
**P2:** pengembangan lanjutan.

## 6. Arsitektur Sistem

```text
                    ┌──────────────────┐
                    │    config.json   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │    config.py     │
                    │ Load + validate  │
                    └────────┬─────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │             services.py             │
          │ Orchestration + cache + normalization│
          └───────┬───────────────────┬─────────┘
                  │                   │
        ┌─────────▼────────┐ ┌────────▼──────────┐
        │  enka_client.py  │ │ hoyolab_client.py │
        │  Enka + Akasha   │ │ HoYoLAB + auth    │
        └─────────┬────────┘ └────────┬──────────┘
                  │                   │
                  └─────────┬─────────┘
                            │
                   Shared domain models
                            │
                 ┌──────────┴──────────┐
                 │                     │
          ┌──────▼──────┐       ┌──────▼──────┐
          │   cli.py    │       │   app.py    │
          │ Rich output │       │ FastAPI/Web │
          └─────────────┘       └─────────────┘
```

### Aturan arsitektur

- CLI dan route FastAPI tidak mengimplementasikan HTTP request provider secara langsung.
- Provider client tidak mengandung kode rendering.
- Model internal tidak bergantung pada struktur JSON mentah provider.
- Kegagalan satu sumber tidak membatalkan hasil sumber lain.
- Semua request jaringan memiliki timeout.
- HTTP client digunakan ulang selama lifecycle proses.
- Fetch independen boleh berjalan paralel dengan batas konkurensi.

## 7. Struktur File

```text
hoyo-akasha-hub/
├── config.json
├── config.example.json
├── config.py
├── models.py
├── services.py
├── cache.py
├── errors.py
├── enka_client.py
├── hoyolab_client.py
├── cli.py
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── character.html
│   └── settings.html
│
├── static/
│   ├── css/
│   │   └── app.css
│   ├── js/
│   │   └── app.js
│   └── fonts/
│       └── JetBrainsMono.woff2
│
└── tests/
    ├── fixtures/
    ├── test_config.py
    ├── test_public_clients.py
    ├── test_hoyolab_client.py
    └── test_api.py
```

### Tanggung jawab modul

| Modul | Tanggung jawab |
|---|---|
| `config.py` | Schema, validasi, pembacaan, penyimpanan konfigurasi |
| `models.py` | Model data internal bersama |
| `services.py` | Penggabungan data dan orchestration |
| `cache.py` | TTL cache dan stale fallback |
| `errors.py` | Error aplikasi yang konsisten |
| `enka_client.py` | Adapter Enka dan Akasha, dipisahkan dalam class |
| `hoyolab_client.py` | Autentikasi, DS, resolusi akun, daily notes |
| `cli.py` | Command, formatting, exit code |
| `app.py` | Route HTML, API lokal, lifecycle aplikasi |

## 8. Konfigurasi

### Contoh `config.json`

```json
{
  "schema_version": 1,
  "game": "genshin",
  "public_account": {
    "uid": "",
    "region": "auto"
  },
  "akasha": {
    "enabled": true
  },
  "hoyolab": {
    "enabled": false,
    "region": "os",
    "game_uid": "",
    "server": "",
    "cookies": {
      "ltuid_v2": "",
      "ltoken_v2": ""
    }
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  },
  "cache": {
    "public_ttl_seconds": 300,
    "ranking_ttl_seconds": 900,
    "notes_ttl_seconds": 60
  },
  "network": {
    "timeout_seconds": 15,
    "max_retries": 2
  },
  "ui": {
    "accent": "amber"
  }
}
```

### Aturan validasi

- UID disimpan sebagai string.
- UID harus berisi digit dan memenuhi aturan game/region yang didukung.
- Jangan menerapkan satu panjang UID universal untuk seluruh game.
- Port harus berada dalam rentang `1–65535`.
- TTL harus berupa bilangan bulat positif.
- Cookie tidak wajib jika HoYoLAB dinonaktifkan.
- Jika HoYoLAB diaktifkan tetapi kredensial belum lengkap, tandai integrasi sebagai `needs_configuration`.
- Konfigurasi autentikasi yang belum lengkap tidak memblokir fitur publik.
- JSON rusak atau schema tidak valid menghasilkan pesan yang menunjuk field bermasalah.
- Penyimpanan menggunakan atomic replace untuk menghindari file terpotong.
- `config.json` masuk `.gitignore`.

### Override melalui environment variable

Minimal:

```text
HOYO_HUB_UID
HOYO_HUB_LTUID_V2
HOYO_HUB_LTOKEN_V2
HOYO_HUB_HOST
HOYO_HUB_PORT
```

**Urutan prioritas:** environment variable → `config.json` → default.

Secret dari environment tidak otomatis ditulis kembali ke file.

## 9. Integrasi Enka dan Akasha

### 9.1 Profil publik

Data yang ditampilkan jika tersedia:

- UID.
- Nickname.
- Adventure Rank.
- World Level.
- Signature.
- Avatar.
- Waktu pengambilan data.

### 9.2 Showcase karakter

Untuk setiap karakter:

- ID dan nama.
- Element.
- Level dan ascension.
- Friendship.
- Constellation.
- Talent level.
- Weapon.
- Artifact.
- Final stats.

Nama, ikon, dan label properti perlu di-resolve dari metadata yang sesuai. Jika metadata gagal dimuat, tampilkan ID atau label fallback yang terbaca.

### 9.3 Statistik karakter

Minimal:

- Max HP.
- ATK.
- DEF.
- Elemental Mastery.
- CRIT Rate.
- CRIT DMG.
- Energy Recharge.
- Elemental/Physical DMG Bonus yang relevan.
- Healing Bonus jika tersedia.

Persentase dan angka absolut harus dibedakan melalui metadata properti, bukan tebakan berdasarkan besar nilai.

### 9.4 Artifact

Minimal:

- Slot.
- Set.
- Rarity.
- Level.
- Main stat.
- Substats.

Jika aplikasi menambahkan **Artifact Crit Value**:

```text
CV = (CRIT Rate × 2) + CRIT DMG
```

Gunakan nilai dalam percentage points, hanya dari substats artifact, dan labeli sebagai **metrik turunan lokal**.

### 9.5 Ranking Akasha

Tampilkan jika tersedia:

- Karakter.
- Nama/kategori leaderboard.
- Posisi.
- Jumlah peserta jika diberikan.
- Percentile jika diberikan atau dapat dihitung dengan denominator yang jelas.
- Asumsi kategori, misalnya weapon/team/ER bracket.
- Waktu data atau waktu fetch.

**Aturan:**

- Tidak ada ranking ditampilkan sebagai “Belum tersedia”.
- Tidak boleh mengubah data kosong menjadi peringkat `0`.
- Ranking build tersimpan tidak boleh dianggap cocok dengan showcase terbaru tanpa identitas build yang dapat diverifikasi.
- Jika kecocokan build tidak dapat dipastikan, beri label “Build Akasha; kecocokan showcase belum diverifikasi”.
- Endpoint dan schema Akasha harus diverifikasi pada tahap discovery; jangan mengasumsikan kontrak API stabil.

## 10. Integrasi HoYoLAB

### 10.1 Alur autentikasi

1. Pengguna mengaktifkan integrasi.
2. Pengguna memasukkan cookie melalui input lokal.
3. Aplikasi memvalidasi akses dengan request provider.
4. Aplikasi mengambil atau memverifikasi game account yang terikat.
5. Jika terdapat beberapa akun, pengguna memilih game UID/server.
6. Aplikasi mengambil daily notes.
7. UI menampilkan status koneksi tanpa mengungkap cookie.

### 10.2 Daily notes Genshin

Jika didukung oleh respons provider:

| Field | Tampilan |
|---|---|
| Current/max Resin | `120 / 200`, mengikuti nilai aktual provider |
| Resin recovery | Durasi menuju penuh dan perkiraan waktu lokal |
| Daily commissions | Jumlah selesai / total |
| Commission reward | Sudah diklaim / belum |
| Expeditions | Jumlah aktif, karakter, status, waktu selesai |
| Realm currency | Nilai sekarang / kapasitas |
| Weekly boss discount | Sisa kesempatan diskon |
| Parametric Transformer | Siap / countdown, jika tersedia |

Field yang tidak tersedia diberi `—` atau “Tidak tersedia”, bukan angka nol.

### 10.3 DS signature

Implementasi harus:

- Menggunakan strategi sesuai endpoint, game, dan region.
- Memperhatikan timestamp, nonce, query, dan body sesuai kontrak provider.
- Menghindari satu formula DS universal.
- Mengisolasi signing dalam helper/adaptor teruji.
- Mengizinkan penggunaan library terpelihara apabila kompatibel dan cukup ringan.
- Menggunakan fixture untuk menguji canonicalization query/body dan hasil signing dengan waktu/nonce terkendali.

### 10.4 Status integrasi

```text
disabled
needs_configuration
connected
expired
verification_required
forbidden
rate_limited
unavailable
```

Jangan menyimpulkan semua HTTP `403` sebagai cookie kedaluwarsa; interpretasikan kode provider jika tersedia.

## 11. CLI

### Command minimum

```bash
python cli.py setup
python cli.py profile
python cli.py showcase
python cli.py character <character-id>
python cli.py rankings
python cli.py notes
python cli.py status
python cli.py serve
```

### Opsi umum

```text
--uid <uid>
--refresh
--json
--no-color
```

`--uid` berlaku untuk data publik. Pemilihan akun notes harus diverifikasi terhadap akun HoYoLAB yang terhubung.

### Contoh

```bash
python cli.py showcase --uid 812345678
python cli.py character 10000046
python cli.py notes --refresh
python cli.py status --json
python cli.py serve --host 127.0.0.1 --port 8000
```

### Ketentuan rendering

- Menggunakan Rich `Table`, `Panel`, dan status indicator seperlunya.
- Kolom angka rata kanan.
- Tidak memakai emoji.
- Mendukung terminal sempit melalui pengurangan kolom atau tampilan vertikal.
- Tidak menggunakan spacing manual untuk membentuk tabel.
- Output `--json` harus JSON valid tanpa spinner atau markup.
- Pesan diagnostik masuk `stderr`.
- Mendukung terminal non-TTY dan `NO_COLOR`.

### Exit code

| Kode | Makna |
|---|---|
| `0` | Berhasil, termasuk hasil kosong yang valid |
| `1` | Error tidak terduga |
| `2` | Input atau konfigurasi tidak valid |
| `3` | Autentikasi diperlukan/gagal |
| `4` | Sumber data tidak tersedia |
| `5` | Rate limit |

Untuk command agregat, hasil parsial ditampilkan dengan jelas; jika ada sumber yang diminta gagal, exit code tetap nonzero.

## 12. Web Dashboard

### 12.1 Arah visual

**Swiss Brutalist / Developer Minimalist.**

Karakter visual:

- Background hitam.
- Border zinc tipis.
- Tipografi monospace.
- Hierarki melalui ukuran teks, spacing, dan garis.
- Panel persegi.
- Data-first.
- Amber atau green sebagai aksen terbatas.
- Tidak ada dekorasi yang menyerupai landing page pemasaran.

#### Larangan

- Gradient.
- Glassmorphism.
- Background blur.
- Glowing orb.
- Emoji.
- Sparkle icon.
- Bento cards dengan hover animation.
- Hero section promosi.
- Drop shadow dekoratif.

#### Design tokens

```css
:root {
  --bg: #000000;
  --surface: #0a0a0a;
  --border: #3f3f46;
  --text: #fafafa;
  --muted: #a1a1aa;
  --accent: #fbbf24;
  --success: #4ade80;
  --danger: #f87171;

  --radius: 0;
  --font-mono: "JetBrains Mono", monospace;
}
```

Font disajikan lokal beserta lisensinya; dashboard tidak bergantung pada CDN font.

### 12.2 Layout utama

```text
HOYO–AKASHA HUB                         LOCAL / GENSHIN
──────────────────────────────────────────────────────
UID [812345678       ] [LOAD]               [SETTINGS]

OVERVIEW   SHOWCASE   RANKINGS   DAILY NOTES
──────────────────────────────────────────────────────
PLAYER                          SOURCE STATUS
Nickname                        Enka       OK
Adventure Rank                  Akasha     CACHED
World Level                     HoYoLAB    DISABLED
──────────────────────────────────────────────────────
CHARACTER        LEVEL    WEAPON              DETAILS
...
──────────────────────────────────────────────────────
Fetched: ...             Cache age: ...       REFRESH
```

### 12.3 Halaman

#### Overview

- Profil publik.
- Status setiap sumber.
- Ringkasan daily notes jika terhubung.
- Timestamp dan freshness.
- Link menuju detail.

#### Showcase

- Daftar karakter.
- Filter element.
- Sort berdasarkan nama atau level.
- Navigasi ke detail karakter.

#### Character Detail

- Identitas karakter.
- Weapon.
- Stats table.
- Artifact table.
- Ranking yang tersedia.
- Informasi sumber dan timestamp.

#### Rankings

- Tabel kategori leaderboard.
- Rank.
- Population jika tersedia.
- Percentile jika tersedia.
- Status kecocokan build.

#### Daily Notes

- Resin dan recovery.
- Commissions.
- Expeditions.
- Resource lain yang tersedia.
- Status autentikasi.

#### Settings

- UID publik.
- Pengaturan Akasha.
- Aktif/nonaktif HoYoLAB.
- Input penggantian cookie.
- Test connection.
- Pemilihan akun game terikat.
- Hapus kredensial.

Cookie tersimpan tidak dikirim ulang ke browser. UI hanya menerima indikator `configured: true/false`.

### 12.4 State wajib

Setiap section memiliki:

- Loading.
- Ready.
- Empty.
- Stale.
- Error.
- Disabled, jika relevan.

Kegagalan HoYoLAB tidak boleh menyembunyikan showcase yang berhasil dimuat.

### 12.5 Responsivitas dan aksesibilitas

- Target viewport minimum: 360 px.
- Tabel besar memakai horizontal scroll di dalam container.
- Navigasi dan form dapat digunakan dengan keyboard.
- Focus indicator terlihat.
- Error tidak hanya dibedakan melalui warna.
- Teks normal memenuhi kontras WCAG AA.
- Countdown tidak diumumkan screen reader setiap detik.

## 13. API Lokal

Prefix: `/api/v1`.

### Endpoint minimum

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/health` | Kesehatan proses lokal, tanpa request provider |
| GET | `/status` | Status integrasi dan cache |
| GET | `/config` | Konfigurasi publik yang telah disanitasi |
| PATCH | `/config` | Mengubah konfigurasi non-secret |
| POST | `/auth/hoyolab` | Menyimpan/mengganti kredensial |
| DELETE | `/auth/hoyolab` | Menghapus kredensial dan cache privat |
| POST | `/auth/hoyolab/test` | Menguji kredensial tersimpan |
| GET | `/accounts/hoyolab` | Daftar akun game terikat |
| GET | `/profile/{uid}` | Profil publik |
| GET | `/showcase/{uid}` | Showcase |
| GET | `/showcase/{uid}/characters/{character_id}` | Detail karakter |
| GET | `/rankings/{uid}` | Ranking Akasha |
| GET | `/notes` | Daily notes akun terpilih |
| POST | `/refresh` | Refresh sumber tertentu |

### Respons sukses

```json
{
  "data": {
    "uid": "812345678",
    "nickname": "Traveler"
  },
  "meta": {
    "source": "enka",
    "fetched_at": "2026-09-27T10:00:00Z",
    "source_updated_at": null,
    "cached": true,
    "stale": false
  }
}
```

`fetched_at` adalah waktu aplikasi mengambil data, bukan jaminan waktu perubahan data di provider.

### Respons error

```json
{
  "error": {
    "code": "HOYOLAB_AUTH_EXPIRED",
    "message": "Sesi HoYoLAB kedaluwarsa. Perbarui cookie.",
    "source": "hoyolab",
    "retryable": false
  }
}
```

### HTTP status

- `400`: input tidak valid.
- `401`: autentikasi dibutuhkan atau kedaluwarsa.
- `403`: akses ditolak/verifikasi diperlukan.
- `404`: resource tidak ditemukan.
- `422`: validasi payload gagal.
- `429`: rate limit.
- `502`: respons provider tidak valid.
- `503`: provider tidak tersedia.
- `504`: timeout provider.

Showcase atau ranking kosong yang valid tetap menggunakan `200` dengan koleksi kosong.

## 14. Cache dan Refresh

### Kebijakan default

| Data | TTL |
|---|---:|
| Enka profile/showcase | 300 detik |
| Akasha ranking | 900 detik |
| HoYoLAB notes | 60 detik |

Nilai ini merupakan default aplikasi; instruksi cache/rate-limit provider harus diprioritaskan jika lebih ketat.

### Ketentuan

- Cache key mencakup source, game, region, UID, dan identitas akun jika relevan.
- Tidak menggunakan token mentah sebagai cache key.
- Request bersamaan untuk resource sama digabungkan menjadi satu fetch.
- Refresh manual melewati TTL lokal, tetapi tetap mematuhi cooldown provider.
- Retry hanya untuk timeout, koneksi gagal, atau error sementara.
- Hormati `Retry-After`.
- Jangan retry berulang untuk cookie kedaluwarsa atau CAPTCHA.
- Jika fetch gagal sementara, cached data boleh ditampilkan dengan label `stale`.
- Penghapusan/penggantian kredensial menghapus cache notes terkait.

**MVP:** cache in-memory. CLI one-shot memiliki cache selama prosesnya berjalan; cache tidak otomatis dibagikan dengan proses web. Persistent cache dapat ditambahkan setelah MVP.

Countdown dihitung lokal dari timestamp target, bukan melalui request per detik.

## 15. Keamanan Lokal dan Privasi

- Server bind ke `127.0.0.1` secara default.
- Semua request provider menggunakan HTTPS.
- Cookie hanya berada di backend.
- Cookie tidak muncul dalam log, exception, JSON response, atau HTML.
- Endpoint notes dan autentikasi menggunakan `Cache-Control: no-store`.
- Konfigurasi berisi secret tidak masuk repository.
- Terapkan izin file terbatas sesuai platform.
- Dashboard meng-escape nickname, signature, dan konten provider.
- CORS lintas origin dinonaktifkan secara default.
- Request perubahan konfigurasi dilindungi pemeriksaan origin dan token CSRF.
- Terapkan validasi host untuk mengurangi risiko DNS rebinding.
- Endpoint sumber data bukan arbitrary URL dari input pengguna.
- Mode akses LAN/remote memerlukan rancangan autentikasi tersendiri dan berada di luar MVP.

Cookie dalam `config.json` adalah penyimpanan plaintext lokal; masking UI tidak dianggap enkripsi.

## 16. Dependency dan Runtime

### Dependency utama

| Library | Fungsi |
|---|---|
| `fastapi` | Server dan API lokal |
| `uvicorn` | ASGI runtime |
| `httpx` | HTTP async |
| `pydantic` | Validasi konfigurasi dan model |
| `rich` | Rendering terminal |
| `jinja2` | HTML templates |

CLI dapat memakai `argparse` bawaan Python agar dependency tetap kecil.

### Dependency pengembangan

- `pytest`.
- `pytest-asyncio`.
- HTTP mocking library, misalnya `respx`.

### Prinsip ringan

- Tidak membutuhkan Node.js untuk menjalankan dashboard.
- Tidak memakai React atau SPA framework pada MVP.
- Tidak membutuhkan database.
- Tidak membutuhkan Redis, Celery, atau Docker.
- JavaScript vanilla untuk fetch, tab/filter sederhana, dan countdown.
- Asset visual karakter boleh dimuat secara lazy.

### Target platform

- Python 3.11+.
- Windows.
- Linux.
- macOS.

**Termux/Android ARM:** target validasi tambahan; dukungannya baru dinyatakan setelah dependency, instalasi, dan runtime diuji pada perangkat nyata.

## 17. Target Performa

Target berikut diukur pada mesin referensi yang dicatat dalam dokumentasi pengujian:

- Startup aplikasi di bawah 3 detik setelah dependency terpasang.
- Respons cache lokal p95 di bawah 100 ms.
- HTML dashboard awal tidak menunggu semua provider selesai.
- Request provider dibatasi timeout default 15 detik per attempt.
- Fetch antar-provider berjalan independen.
- Idle memory target di bawah 150 MB pada konfigurasi single-worker.
- Tidak ada background polling ketika integrasi dinonaktifkan.
- Auto-refresh web berhenti ketika tab tidak aktif.
- Satu refresh UI tidak menghasilkan request provider duplikat.

## 18. Error dan Recovery

| Kondisi | Perilaku |
|---|---|
| UID tidak valid | Validasi sebelum request |
| Profil tidak ditemukan | Empty/error state yang spesifik |
| Showcase tidak dipublikasikan | Jelaskan bahwa showcase harus tersedia publik |
| Ranking tidak tersedia | Tampilkan “Belum tersedia” |
| Cookie kedaluwarsa | Minta pembaruan cookie |
| Verifikasi akun dibutuhkan | Tampilkan status dan arahkan ke aplikasi/situs resmi |
| Daily notes tidak diizinkan | Jelaskan pengaturan akun perlu diperiksa |
| Provider timeout | Tampilkan stale cache jika ada |
| Provider rate limit | Tampilkan cooldown, hindari retry agresif |
| Schema provider berubah | Error terstruktur, sumber lain tetap berjalan |
| Metadata karakter gagal | Gunakan ID/label fallback |
| Konfigurasi rusak | Pesan field/path yang jelas tanpa membocorkan secret |

## 19. Acceptance Criteria

### AC-01 — Mode publik mandiri

**Given** hanya UID dikonfigurasi  
**When** pengguna membuka showcase  
**Then** profil dan karakter publik dapat dimuat tanpa cookie.

### AC-02 — Isolasi kegagalan

**Given** Enka berhasil dan Akasha gagal  
**When** dashboard dimuat  
**Then** showcase tetap tampil dan hanya section ranking menunjukkan kegagalan.

### AC-03 — HoYoLAB opsional

**Given** integrasi HoYoLAB dinonaktifkan  
**When** aplikasi berjalan  
**Then** tidak ada request HoYoLAB dan notes menampilkan status disabled.

### AC-04 — Kredensial terlindungi

**Given** cookie sudah disimpan  
**When** pengguna memanggil `/config`, `/status`, atau melihat dashboard  
**Then** nilai cookie tidak muncul.

### AC-05 — Akun privat terverifikasi

**Given** UID publik berbeda dari akun HoYoLAB  
**When** daily notes dimuat  
**Then** notes menggunakan akun terikat yang dipilih dan menampilkan UID-nya secara eksplisit.

### AC-06 — Data kosong benar

**Given** karakter tidak memiliki ranking  
**When** ranking dirender  
**Then** aplikasi menampilkan unavailable, bukan rank `0`.

### AC-07 — Cache konsisten

**Given** cache masih valid  
**When** resource yang sama diminta ulang  
**Then** provider tidak dipanggil kembali.

### AC-08 — CLI machine-readable

**Given** command menggunakan `--json`  
**When** dijalankan  
**Then** `stdout` berisi JSON valid tanpa Rich markup atau spinner.

### AC-09 — Tampilan mobile

**Given** viewport 360 px  
**When** dashboard dibuka  
**Then** kontrol utama tetap dapat digunakan dan tabel tidak memperlebar seluruh halaman.

### AC-10 — Konsistensi data

**Given** fixture respons provider yang sama  
**When** diproses melalui CLI dan API  
**Then** nilai domain hasilnya identik.

## 20. Strategi Pengujian

### Unit test

- Validasi dan precedence konfigurasi.
- Redaksi secret.
- Parsing stats dan artifact.
- Konversi persentase.
- Interpretasi ranking.
- Cache TTL dan invalidation.
- DS signing sesuai strategi yang diverifikasi.
- Normalisasi error provider.

### Integration test dengan fixture

- Enka sukses dan showcase kosong.
- Akasha ranking tersedia/tidak tersedia.
- HoYoLAB sukses, expired, dan verification required.
- Timeout, rate limit, serta malformed response.
- Request deduplication.
- Endpoint konfigurasi tidak membocorkan cookie.
- CSRF/origin validation pada operasi perubahan.

### Smoke test manual

- Instalasi bersih.
- Setup hanya UID.
- CLI dan dashboard.
- Autentikasi menggunakan akun penguji.
- Layout desktop/mobile.
- Keyboard navigation.
- Shutdown menutup HTTP client dengan benar.

Live API test bersifat opt-in dan tidak menjadi syarat test suite standar.

## 21. Tahapan Implementasi

### Tahap 0 — Verifikasi integrasi

- Verifikasi endpoint, schema, dan batas Enka/Akasha.
- Verifikasi autentikasi serta DS HoYoLAB untuk region target.
- Kumpulkan fixture yang telah disanitasi.
- Catat metode yang didukung dan keterbatasannya.

**Hasil:** kontrak adapter yang dapat diuji.

### Tahap 1 — Fondasi

- Struktur project.
- Config loader.
- Domain models.
- Error types.
- Shared HTTP client.
- Cache.

### Tahap 2 — Data publik dan CLI

- Enka profile/showcase.
- Akasha ranking.
- Rich rendering.
- Output JSON.
- Partial failure handling.

### Tahap 3 — HoYoLAB

- Penyimpanan cookie.
- Test connection.
- Pemilihan akun terikat.
- Daily notes.
- Penanganan auth error.

### Tahap 4 — Dashboard

- FastAPI endpoints.
- Jinja templates.
- Desain Swiss Brutalist.
- Fetch independen per section.
- Settings dan refresh.

### Tahap 5 — Validasi rilis

- Pengujian integrasi.
- Audit kebocoran secret.
- Pengukuran performa.
- Dokumentasi instalasi dan troubleshooting.

## 22. Definition of Done

MVP selesai ketika:

- Semua fitur P0 dan acceptance criteria terpenuhi.
- CLI dan dashboard menggunakan service layer yang sama.
- Fitur publik bekerja tanpa autentikasi.
- Integrasi privat memiliki status dan error yang jelas.
- Tidak ada kredensial dalam repository, log, atau respons API.
- Tidak ada nilai data palsu untuk menggantikan field yang tidak tersedia.
- Dashboard mengikuti aturan visual dan responsivitas.
- `requirements.txt` mencantumkan versi dependency yang telah diuji.
- README menjelaskan setup UID, cookie, CLI, server, serta keterbatasan provider.
- Pengujian standar tidak membutuhkan cookie pribadi atau jaringan live.

**Hasil akhirnya:** aplikasi lokal yang berfokus pada data, ringan dijalankan, dan tetap berguna meskipun hanya satu sumber data tersedia.
