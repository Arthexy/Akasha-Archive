# Redesign verification — 1 October 2026

Implemented from PRD-Redesign-HoYo-Akasha-Hub.md: archive palette, Indonesian UI, responsive shell, native navigation dialog, portrait grid, separate build detail, flat artifact substats, category ranking dialog, private-account notes, three settings groups, local deletion confirmation and preserved accent preferences. No new production frontend dependencies.

## Automated checks

- Existing Python suite: 28 passed; temporary-file access required running outside the Windows sandbox. Existing Python 3.14 asyncio deprecation warnings remain.
- `node tests/test_frontend.cjs`: null versus zero, small positive percentage precision, escaped provider text, missing ranking values last in both directions, pagination clamp, detail/back, late UID A response after B, late notes response after private-account change, cooldown controls.
- JavaScript syntax check passed. Impeccable mechanical detector returned an empty finding list.
- Security, host policy, CSRF, redaction and bound-account backend tests remained passing.
- Core CSS and JS total about 15 KB when gzip-compressed locally (asset size, not a measured network transfer). Token text contrast across the three reading surfaces: 6.78:1 minimum for tested primary, secondary, accent, success and error combinations. This does not certify every rendered control or WCAG compliance.

## Browser checks

Labelled offline fixture on port 8001, not injected into the normal application. Checked entry, account load, search, filtered character detail with five artifact slots, return with preserved filter/focus, ranking pagination and sort, category dialog Escape/focus restoration, notes showing private UID, valid Resin zero and unavailable commissions/currency, mobile navigation Escape/focus restoration, and three settings groups.

Ranking reflow checked at requested widths 360, 390, 768, 1280 and 1440; DOM widths did not exceed viewport. Desktop and mobile screenshots were inspected in one batch and material issues fixed (unavailable resource text size, unavailable rank prefix). A confirmation pass covered mobile notes and settings. The in-app browser's viewport and screenshot sizes later differed from requested sizes, so exact screenshot pixel dimensions are not certified.

## Validation still required

This is an implementation and local regression check, not a claim that every PRD P0 acceptance criterion has passed. No five-player usability study, full screen-reader audit, exhaustive zoom/browser/device matrix, LCP/CLS timing measurement, authenticated provider verification, cookie-expiry/multiple-private-account end-to-end test, or complete live artwork performance measurement was performed. The fixture deliberately exercises missing-image fallbacks; live provider image sizes and licensing were not newly audited. High-resolution splash artwork and View Transitions remain optional P1.

Existing portrait URLs and image proxy are preserved. JetBrains Mono remains local under its included OFL; body/display use system font fallbacks. Numeric talent IDs show numbered talents with source levels because the current model does not supply verified functional talent names.

## Revisi Fix.md — 1 Oktober 2026

- Stat diberi SVG kecil sesuai kategori; gambar senjata/artifact memakai icon item aktual dari Enka, namecard memakai playerInfo.namecardId.
- Tiga ikon resource game disimpan lokal (~11 KB). Metadata/gambar yang tidak tersedia tetap menyisakan teks yang dapat dibaca.
- Ringkasan menyimpan maksimal 20 UID dan nickname publik di localStorage browser. Hanya profil yang berhasil dimuat dicatat; duplikat dipindah ke urutan terbaru. Ada aksi menghapus riwayat. Cookie tidak masuk riwayat.
- Sidebar desktop bisa ditutup/dibuka. Mobile memakai lima tab bawah dengan safe-area padding dan state aktif showcase saat detail dibuka.
- Ranking membuka detail karakter yang cocok berdasarkan ID; build privat/tidak tersedia diberi keterangan. Filter dibersihkan dan halaman showcase disesuaikan agar kembali ke karakter yang dipilih.
- Animasi profile 260 ms memakai transform/opacity, tanpa library/timer baru; prefers-reduced-motion menonaktifkan animasi.
- Validasi: 29 test Python lulus (199 warning deprecation dependency), pemeriksaan frontend offline dan syntax lulus. Browser fixture memverifikasi dua akun di riwayat, sidebar toggle, ranking ke Ayaka, enam gambar equipment termuat, namecard termuat, dan tiga ikon resource termuat. Pada viewport 390 px tidak ada overflow horizontal dan tab bawah tampil. Screenshot revision-preview.png berisi data fixture berlabel.
- Server nyata dijalankan ulang pada 127.0.0.1:8000. Verifikasi visual menggunakan fixture, bukan koneksi HoYoLAB nyata.

## Revisi lanjutan Fix.md — 1 Oktober 2026

- Ikon stat SVG diganti PNG stat dari koleksi EnkaCardData, disimpan lokal dan dipetakan per kategori HP/ATK/DEF/CRIT/ER/EM/bonus damage. Simbol navigasi mempertahankan SVG mobile yang diminta pengguna.
- Gambar equipment diberi surface gelap dengan padding. Artifact memakai grid media/teks; ranking memakai kolom portrait dan teks, dengan jarak baris dan kategori yang lebih rapi.
- Sidebar desktop tetap terlihat secara default dan memakai lima ikon yang sama dengan tab bawah HP. Tombol icon kecil mengontrol collapse sidebar. Branding tampilan menjadi Teyvat Archive dengan lambang kompas geometris.
- Tiga metric profil memakai grid dengan tinggi label konsisten. Browser memverifikasi strong Adventure Rank, World Level, dan showcase memiliki posisi top identik di desktop maupun viewport 390 px.
- Bahasa Indonesia/English disimpan melalui ui.language di konfigurasi. Penyimpanan preferensi memuat ulang halaman. Label stat/nama karakter/item/kategori dan teks provider dipertahankan. Angka serta waktu mengikuti locale UI. Template HTML hanya menerjemahkan segmen tulisan aplikasi, bukan interpolasi data provider.
- Animasi perpindahan view 380 ms, profil 420 ms, hover card/navigation 200–240 ms memakai CSS transform/opacity. Tanpa dependency atau polling animasi baru; reduced-motion mematikan transisi/animasi.
- Validasi: 30 test backend lulus (199 warning deprecation dependency), frontend/syntax lulus. Browser memverifikasi perpindahan id → en → id, label ranking English, format angka, sidebar berisi lima ikon, detail karakter sesuai ID, ikon stat pada viewport terlihat, dan tidak ada overflow halaman mobile. Data visual adalah fixture berlabel; koneksi HoYoLAB asli tidak diuji.

## Revisi terakhir — 1 Oktober 2026

- Sidebar desktop kini menyusut menjadi rail ikon 76 px, tidak hilang. Logo cross-fade ke glyph sidebar saat hover/focus, label fade/blur saat collapse, lebar rail bertransisi 360 ms, dan surface sidebar memakai blur 6 px. Tooltip native mempertahankan nama tab ketika collapsed.
- Copy UID dan tooltip pada metric showcase dihapus. Hover category/sort/text buttons mendapat padding agar teks tidak menempel.
- Gambar senjata desktop berukuran 260 × 260 px (mobile 240 px), memakai object-fit contain.
- Lima tema: amber, green, ocean, violet, rose, masing-masing memakai surface/accent dan radial background statis. Tidak ada animasi background atau library baru.
- Akar masalah namecard nyata: Enka memakai nameCardId, dan item 210182 hanya ada di store/gi/namecards.json dengan key Icon/path JPG. Adapter menggabungkan katalog baru dan lama serta memakai PNG variant yang tersedia. API akun 884152734 menghasilkan UI_NameCardPic_FD3_P.png; browser aplikasi nyata memverifikasi naturalWidth > 0. final-revision-preview.png memakai akun publik nyata.
- Validasi: 31 test backend dan regresi frontend lulus. Browser mengecek collapse rail, lima opsi tema, theme violet, ukuran weapon, mobile tanpa overflow, dan tidak ada Copy UID.
- Bind 100.97.223.11:8000 gagal; pemeriksaan Get-NetIPAddress tidak menemukan IP tersebut pada host. Server terbaru berjalan di loopback 127.0.0.1:8000. Setelah Tailscale/IP tersedia, jalankan .venv\Scripts\python cli.py serve --host 100.97.223.11.

## Revisi grup — 1 Oktober 2026

- Branding desktop hanya tampil di sidebar; mobile menampilkan satu branding di topbar. Sidebar/topbar/bottom tabs memakai surface gelap transparan dengan blur tetap 14–16 px.
- Pagination ranking dan showcase memakai fade/translate 300 ms pada list yang baru dirender. Controls tetap; prefers-reduced-motion melewati animasi.
- Weapon memakai layout media kiri dan informasi kanan, tanpa padding internal pada gambar agar artwork mengikuti luas background. object-fit contain dipertahankan.
- Resource memakai grup surface dengan icon di kiri label. Ringkasan resin mengikuti susunan yang sama. Daily commission menggunakan PNG ungu yang diberikan pengguna (Pasted image 20261001143054.png).
- Ranking memakai grup horizontal melalui table border-spacing 14 px, tanpa separator row; category dan view-build memakai bordered buttons. Mobile tetap grup vertikal.
- Browser fixture memverifikasi satu branding desktop, row tanpa border, pergantian ranking/showcase ke halaman 2 tanpa error, padding weapon 0 px, resource heading flex, dan mobile 390 px tanpa overflow. grouped-revision-preview.png memakai fixture berlabel.

## Snapshot Akasha — revisi 1 Oktober 2026, 15:40

- Skill Impeccable dan Ponytail dipakai. Ranking membuka build melalui area karakter berwarna; tidak ada lagi tombol showcase di ranking.
- Snapshot weapon/stat/talent berasal dari build list yang cocok persis dengan hash kalkulasi. Lima artifact berasal dari endpoint publik /api/artifacts/UID/HASH. Tidak ada fallback pencocokan nama atau equipment Enka.
- Endpoint lokal menolak hash invalid dan hash yang tidak ada pada ranking UID. Payload hanya field build yang dibutuhkan, tanpa metadata owner.
- Category dan set ringkas dengan ellipsis/title; 4pc menghilangkan potongan 1pc, 2+2 tetap dua set. Dialog mempertahankan seluruh asumsi.
- Artifact tanpa padding internal, panel asumsi/status memakai grup warna, weekly boss/transformer memakai resource mini dan PNG pengguna. Sorting/paging serta disclosure/dialog beranimasi dan menghormati reduced motion.
- 34 tes backend lulus; pemeriksaan frontend lulus. Browser fixture memverifikasi desktop/mobile, weapon snapshot berbeda dari Enka, resource mini, dialog, source groups, dan navigasi kembali/reload.
- Integrasi nyata endpoint lokal UID 884152734: source akasha, Ayaka/Amenoma Kageuchi, 5 artifact, hash ranking sama. Server aktif di 127.0.0.1:8000.
- akasha-revision-preview.png adalah proof fixture offline yang diberi label, bukan data akun nyata.
# Explore World — 2026-10-02

New `/explore` route and `/api/v1/explore` endpoint use the selected bound HoYoLAB account, independently of the public showcase UID. Cached for the existing public TTL; refresh uses the shared CSRF-protected endpoint. Account changes invalidate frontend data and discard in-flight responses.

Region cards show provider main-area progress, statue levels, reputation, Natlan tribes, offerings and subareas. Boss data is omitted. Special maps are separate; parent/child areas are counted once. Chasm surface and Underground Mines retain their individual progress. Chenyu combines its three available leaf areas. Frost Moon is shown separately using the provider's Dark Side of the Moon area and remains included through Nod-Krai's aggregate.

Total is an equal-weight average of selected regional averages, explicitly described in the UI. It is not weighted by geographic area or chest count. Missing progress is excluded; zero remains zero. Progress above100% from HoYoLAB is capped100%. Selected regions persist locally per bound account. Unknown standalone regions remain selectable.

Real official game artwork and map icons are recorded in `static/images/explore/sources.json`. Broken Natlan/Nod-Krai image URLs were verified404; official map logos replace their icons. Their provider background illustrations and some newer offering icons remain unavailable; failed images are hidden and labels/levels stay readable.

Validation:39 backend tests passed; frontend checks cover calculation, per-account selection, stale account responses and existing regressions. DOM reflow checked at1440x1000 and390x844 with no horizontal overflow. Live selection changed total83.9%→87%→83.9% when excluding/reincluding Liyue. Detector returned no findings. Native-size screenshot `explore-user.png` is valid; explicit-viewport screenshots have a Windows140% DPI capture mismatch and should not be used as complete visual proof.

Reviewer disposition: ship, with scoped visual signoff. Material findings: none. The native `.impeccable/review/explore-user.png` capture establishes only its visible partial viewport; complete desktop/mobile visual coverage is unverified. DOM reflow checks are separate evidence from screenshot coverage.

Documentation comparison: Explore World extends the incumbent ocean theme, existing card surfaces and typography with official region imagery, native disclosures, three columns on wide desktop, two at the intermediate breakpoint, and one on mobile. Existing DESIGN.md predates several already-implemented theme/navigation changes; this is pre-existing documentation drift. No durable system change was approved for this extension, so DESIGN.md is preserved. The document reference does not require a new surface brief for this incumbent extension.

# Fix.md follow-up — 2026-10-02

Explore World: Lunar Island and Moontide area aliases move into Frost Moon; Windrest Peak groups with Mondstadt even when returned as a root. These changes preserve the provider's main aggregate and avoid adding extracted moon areas twice. Region and special-map checkboxes share their group selection and synchronize immediately. Total exploration appears above the grids in a wide surface. Detail/reputation disclosures reuse the source-status animation, including interruption and reduced-motion handling. Explore cards use the existing desktop zoom/sweep language with touch and reduced-motion exclusions.

The three user-supplied images in Fix.md now provide Temple of Space, Frost Moon, and Ancient Sacred Mountain backgrounds; provenance is recorded in sources.json. Region logos use a light silhouette for contrast. Attempts to retrieve Natlan/Nod-Krai backgrounds from the official CDN returned 404; Fandom returned 403. Existing provider backgrounds remain the fallback.

Validation: 40 backend tests passed; frontend regression checks and JavaScript syntax check passed. Added checks for moon regrouping, Windrest ownership, total placement, and shared checkbox availability. In-app browser rejected the local preview with ERR_BLOCKED_BY_CLIENT, so desktop/mobile visual and live animation verification remain unverified. Impeccable detected four pre-existing sidebar layout-transition warnings outside this change. Fix.md item 8 ends after “dan”; only its explicit request to match existing animation was implemented.

# Fix.md revision — 2026-10-02 16:57 WIB

Implemented all eight revised items. Removed color sweeps from Explore, showcase, and ranking while preserving zoom; Expeditions explicitly retain the requested horizontal sweep and zoom at 480 ms. Windrest Peak is a detail area of Mondstadt, preserving Mondstadt's provider aggregate whether Windrest arrives as a root or child. Supplied Natlan/Nod-Krai images are installed and recorded in sources.json. Image fade was already uniform across Explore headers and remains unchanged per item 6. Progress bars animate increases/decreases with a left-anchored scale and reduced-motion handling. Sidebar transitions are 320 ms; compact buttons measure 44×44 px with 10 px corners. Ranking offers See Detail in the existing Akasha snapshot viewer and an independent Akasha link; missing snapshots do not fabricate a local detail destination.

Verification: backend suite passed 40 tests; frontend regression checks cover both links, missing snapshots, increasing/decreasing progress, duration, and reduced motion. Local offline preview now includes exploration, expeditions, and Akasha snapshots. Browser inspection verified Windrest placement, regional image loading, selection totals, local Akasha detail source, compact-sidebar geometry/timing, and no document overflow at 1440 px desktop or 390 px mobile on inspected surfaces. Preview data remain explicitly labeled fixtures. Real upstream Akasha/HoYoLAB requests were not necessary for this revision.

# Fix.md revision — 2026-10-02 18:18 WIB

Implemented the four new revisions: region backgrounds retain full opacity with mild brightness/saturation enhancement and a bottom fade; Expeditions rows span the same width as the resource section and retain only zoom; sidebar navigation keeps one height, padding, alignment, and gap in both states, with labels contracting/expanding through the same max-width transition; exploration fills are assigned through CSSOM rather than inline markup.

Root cause of the full-length progress bar: production CSP has `style-src 'self'`, so the inline `style="transform:scaleX(...)"` emitted by the previous implementation was rejected. Removed that attribute and kept CSP unchanged. The fill now starts at zero in the stylesheet and receives its actual scale through the shared rendering function, including first render and reduced motion. The preview now uses the same CSP so this failure is reproducible during future visual checks.

Validation: 40 backend tests and frontend regression checks passed. Added checks for first-render 81.9% scaling and absence of inline style markup. Browser measured all settled progress fills against their declared values under CSP (including 56.67%, 80%, 70%, 60%, and 40%); a checkbox change showed an intermediate animated scale before reaching the new value. Desktop Expeditions rows and the resource section both measured 1101 px; all five rows matched. At 390 px mobile there was no horizontal document overflow, and rows measured 343 px. Desktop/mobile screenshots checked the brighter region artwork and layout; no browser console errors were reported. Sidebar was exercised in both directions, with matching 44 px button heights throughout the transition. Impeccable's remaining max-width/width warnings reflect the explicitly requested bounded sidebar resizing.

