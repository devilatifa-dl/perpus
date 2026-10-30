# PRD — Perpustakaan SMA Negeri 1 Abung Tengah

## Problem statement (original)
Web perpustakaan sekolah dengan design modern & keren untuk SMA 1 NEGERI ABUNG TENGAH (Jln Raya Subik, Desa Pekurun Selatan). Fitur: tambah/hapus buku, tambah/cetak anggota, kartu anggota digital, scan QR untuk pinjam/kembalikan, laporan buku masuk & hilang, laporan harian & bulanan, susunan rak, tanpa denda. 3 peran: admin, petugas, siswa.

## Users & portal (alamat terpisah — keputusan user 11 Okt 2026)
- `/` : halaman pemilih portal
- `/admin` : Admin & Petugas (akses penuh: buku, anggota, sirkulasi, laporan, desain kartu)
- `/siswa` : Siswa — HANYA LIHAT DATA BUKU (katalog & rak). Tidak ada kartu/riwayat/anggota.
- Backend menolak login siswa di portal admin & sebaliknya (field `portal` di body login). Endpoint members/transactions/reports/incoming/settings PUT = staff only.

## Implemented
### 11 Okt 2026 (sesi awal)
- Auth JWT cookie httpOnly + rate limiting; CRUD buku (sampul base64) & anggota (foto); kartu anggota + QR; QR scanner kamera + input manual; rak dengan kapasitas; laporan transaksi harian/bulanan; dashboard.
### 11 Okt 2026 (sesi ini)
- Buku Masuk: form (judul, penulis, jumlah eksemplar, tanggal, sumber, kategori, rak, sampul) → POST /api/incoming membuat N buku nyata + catatan laporan. Dashboard `incoming` = total eksemplar nyata.
- Lapor Hilang: tombol di daftar koleksi → PATCH /api/books/{id}/status {Hilang|Tersedia, note}. Buku tetap di koleksi berstatus Hilang, bisa "Ditemukan" (laporan hilang berubah status Ditemukan).
- Riwayat Anggota: GET /api/members/{id}/history (pinjam + returned/returned_at, total, active) tampil di detail anggota (/admin).
- Anggota: kolom email & no HP dihapus (schema + form + kartu).
- Logo sekolah (`/logo-sekolah.png`) & logo perpustakaan "EKLIPS_SMANSA" (`/logo-perpustakaan.png`) dari user; tampil di login, chooser, sidebar, topbar, kartu, header cetak laporan. Bisa diganti via desain kartu (settings).
- Desain kartu anggota: tema (navy, emerald, maroon, sunset, midnight, light), susunan (classic, modern, portrait), judul kartu, toggle QR & alamat, unggah logo. Disimpan GET/PUT /api/settings.
- Laporan: tab Buku Masuk & Buku Hilang pakai data nyata + filter periode + ringkasan; header cetak berlogo.
- Portal terpisah /admin & /siswa + halaman pemilih `/`.
### 11 Okt 2026 (sesi lanjutan)
- Ekspor PDF laporan (reportlab, `backend/reports_pdf.py`): GET /api/reports/export.pdf?type=transaksi|masuk|hilang&period=semua|harian|bulanan — kop berlogo (logo dari settings atau bawaan di `backend/assets/`), ringkasan, tabel, blok tanda tangan petugas. Tombol "Unduh PDF" di Laporan.
- Laporan transaksi berbasis **loans** (pasangan pinjam↔kembali): kolom Tgl Pinjam, Tgl Kembali, status Dipinjam/Dikembalikan (`build_loans`). GET /api/reports mengembalikan `loans`.
- Dialog Lapor Hilang (modal): catatan + nama pelapor (default nama user, dikirim sebagai `reporter` → `reported_by`); modal konfirmasi untuk "Ditemukan".
- Cetak Massal Kartu: Anggota → "Cetak massal" → tampilan lembar A4, filter kelas, ukuran ID 85,6×54 mm (10/halaman; layout potret 54×85,6 mm, 8/halaman) mengikuti desain kartu tersimpan. Pakai CSS `zoom` + `@page A4`.
- Portal siswa: lokasi rak di tiap kartu katalog (nama rak + tombol "Lihat rak" → tab Rak dengan sorotan), chip filter per rak.
- Keputusan user: siswa hanya boleh melihat data buku (katalog & rak) — tab kartu/riwayat dihapus; endpoint anggota/riwayat/laporan/transaksi staff-only.
- Refactor: komponen dipecah ke `src/components/*` (Login, Shared, MemberCard, CardDesigner, MemberHistory, IncomingForm, Shelves, StudentPortal, PortalChooser) + `src/lib.js`.

### 11 Okt 2026 (sesi lanjutan 2) — "buat secara sederhana"
- Pengingat Kembali: GET /api/overdue (loan Dipinjam > 7 hari, `days_out`), panel di Ringkasan + badge dashboard. Seed TRX-001 dimundurkan 10 hari sebagai contoh.
- Ekspor Excel: GET /api/reports/export.xlsx (openpyxl, kop berlogo, header baris 7) + tombol "Excel" di Laporan.
- Reservasi Buku (antrean saja, buku TIDAK dikunci; maks 3 aktif; tidak boleh duplikat; buku Hilang tidak bisa dipesan): siswa `POST/GET mine/DELETE /api/reservations`, tab "Pesanan saya" + tombol "Pesan buku" di katalog (menampilkan jumlah antre). Petugas: panel "Antrean pesanan siswa" di Ringkasan & Sirkulasi → Pinjamkan (buat transaksi pinjam, status Dipinjamkan) / Tolak.
- Stok Opname: Rak buku → "Mulai stok opname": pilih rak, pindai QR / ketik kode, centang per buku, deteksi salah rak, Selesai → simpan POST /api/stocktake; buku tidak terpindai diputuskan satu per satu (tombol tandai hilang → modal). Badge "Opname terakhir".
- QRScanner dipindah ke `components/QRScanner.js`.

### 15 Okt 2026 — sesi Devi Latifa
- Teks: nama sekolah → "SMA NEGERI 1 ABUNG TENGAH" (semua UI, PDF/Excel, default kartu + migrasi settings); nama admin "Administrator" → "Devi Latifa" (seed + migrasi); hero siswa "HALO SISWA/SISWI SMANSA".
- Stok buku (keputusan user: satu judul, satu QR, ada angka stok): field stock/borrowed/lost/available, status dihitung (Tersedia/Dipinjam/Hilang/Habis). Migrasi `normalize_books()` menggabungkan buku judul+penulis sama (remap transaksi/pesanan/laporan). Pinjam −1 tersedia, kembali +1 (atomic), anggota tak boleh pinjam judul sama 2x, kembali hanya jika anggota memang meminjam. Tambah buku / buku masuk judul sama → menambah stok. PATCH /api/books/{id}/stock. Hilang/ditemukan per eksemplar. Tombol QR label per judul.
- Pengunjung (`backend/visits.py`, menu Pengunjung): scan QR kartu/NIS (kamera kontinu atau alat pemindai USB/ketik) → scan 1 masuk, scan 2 keluar (penjaga dobel-scan 30 dtk); tamu tanpa kartu (nama, asal, keperluan); catat keluar manual, hapus; auto keluar jam sekolah (bawaan 14:00 WIB, bisa diubah, dijalankan saat data dibuka — check_out diset tepat jam tsb). Ringkasan di dashboard.
- Laporan: tab Kunjungan (+PDF/Excel) & Statistik & persentase (per hari, per kelas %, anggota vs tamu %, cara keluar %, jam kedatangan, rincian harian; PDF/Excel type=statistik).

### 15 Okt 2026 (lanjutan)
- Peringkat Rajin Berkunjung: GET /api/visits/leaderboard?month=YYYY-MM (10 besar siswa + peringkat kelas dengan %, hanya kunjungan anggota). Tab di Laporan (podium, PDF/Excel type=peringkat&period=YYYY-MM) dan tab "Peringkat" di portal siswa (menyorot "kamu" berdasarkan nama terpilih).
- Edit buku: PUT /api/books/{id} (judul, penulis, kategori, rak, ISBN, sampul; tolak duplikat judul+penulis; judul baru diteruskan ke transaksi/pesanan/laporan hilang). Tombol Atur stok kini ikon Layers.
- Rak: POST/PUT/DELETE /api/shelves (ganti kode memindahkan buku otomatis; hapus rak berisi buku wajib pilih rak tujuan; minimal 1 rak). UI ShelfManager di menu Rak buku.
- Teks "kunjungan" → "Pengunjung" di UI & judul PDF (opsi keperluan tamu "Kunjungan dinas" tetap).
- Modal kini bisa ditutup dengan tombol Escape.

### Okt 2026 — "lanjutkan projek ini" (Fase 1)
- Scan QR diperbaiki: komponen baru `CameraScanner` (start/stop kamera berurutan, jadi tidak bentrok di React StrictMode atau saat ganti kamera; tombol ganti kamera depan/belakang; pesan izin/kamera tidak ada/HTTPS + tombol Coba lagi). Dipakai di Pengunjung dan modal QRScanner (+ input kode manual). Notifikasi "Kunjungan tercatat".
- Saklar izin upload foto anggota (menu Pengaturan sudah dihapus; sekarang hanya lewat tombol "Foto siswa" di halaman Anggota) → PUT /api/settings/photo-upload (`member_photo_upload`). Saat ditutup, server menolak unggahan dari siswa dan tombol di portal siswa dikunci. Admin/petugas selalu bisa.
- Foto anggota disimpan di Emergent Object Storage (`backend/media.py`): POST /api/uploads/photo → otomatis dikompres (Pillow + pillow-heif, orientasi EXIF dibetulkan, sisi terpanjang 1080 px, JPEG q90→60 sampai ≤500KB). GET /api/files/{path} hanya untuk pengguna yang sudah login. member.photo = "/api/files/...".
- Laporan → tab "Ringkasan & grafik" (`backend/summary.py` GET /api/reports/summary?start&end&group=day|month): kartu angka, grafik sirkulasi & pengunjung, buku terpopuler, anggota paling aktif, ekspor CSV, Cetak/PDF.
- Akun login anggota: admin membuatnya di Anggota → ikon kunci (GET/PUT/DELETE /api/members/{id}/account). Akun anggota masuk ke /siswa lalu membuka tab "Profil saya" (kartu, upload foto, riwayat pinjam lewat GET /api/account/history). Akun siswa bersama tetap bisa dipakai.

### Okt 2026 — Impor Excel & kartu bagian belakang
- Impor anggota massal sekarang hanya menerima Excel (.xlsx); CSV ditolak. Template Excel tersedia dari GET /api/members/import-template.xlsx, dan NIS angka tidak berubah jadi ".0".
- Bagian belakang kartu anggota (`MemberCardBack`): judul, daftar peraturan/syarat & ketentuan (satu baris = satu poin), dan teks web. Semuanya bisa diedit di Desain kartu (settings card_back_title/card_back_rules/card_back_web). Tersedia tombol Depan/Belakang di pratinjau, dan cetak massal bisa memilih sisi belakang dengan kolom dicerminkan untuk cetak bolak-balik.
- Ukuran kartu cetak massal 86 × 56 mm (8,6 × 5,6 cm), 10 kartu per A4 (jarak baris 1,5 mm, margin 5 mm); potret 56 × 86 mm, 9 per A4.
- Cetak dua sisi: Cetak massal → Sisi "Dua sisi (bolak-balik)". Halaman depan dan belakang disusun bergantian, satu halaman A4 per lembar, dan kolom sisi belakang dicerminkan. Bug cetak massal yang menghasilkan halaman kosong sudah diperbaiki (tampilan cetak sekarang dipasang langsung di body).
- Pengunjung: kolom kode sekarang juga mencari nama/NIS dengan daftar saran (bisa diklik atau dipilih dengan panah + Enter).
- Kamera QR: kalau kamera belakang gagal, otomatis mencoba kamera lain. Setelah scan muncul layar hijau "Berhasil" (atau merah kalau gagal) selama 1 detik, lalu siap scan lagi. Kode yang sama diabaikan selama 5 detik, dan pesan error menampilkan kodenya.
- Tombol cepat "Foto siswa: Aktif/Nonaktif" di halaman Anggota untuk menyalakan atau mematikan izin upload foto siswa.
- Potong foto (react-easy-crop, rasio 6:7): foto digeser/diperbesar dulu sebelum diunggah, dan ada tombol "Atur posisi" untuk foto yang sudah ada. Untuk HEIC yang tidak bisa dibuka browser, foto diunggah dulu lalu dipotong. Modal bertumpuk sekarang hanya menutup modal paling atas.

## Backlog (berikutnya)
- Fase 2: denda keterlambatan otomatis, notifikasi jatuh tempo, izin upload per anggota/berjadwal
- Fase 3: cetak massal kartu ber-QR (sudah sebagian), reservasi lanjutan, laporan bulanan otomatis

## Tech stack
Backend FastAPI + MongoDB (motor). Frontend React + react-router-dom + Tailwind (preflight) + CSS kustom (App.css, Card.css, Portal.css). QR: html5-qrcode; QR gen: api.qrserver.com.

## Known constraints
- Foto anggota di object storage; logo & sampul buku masih base64 di MongoDB (maks 900KB).
- QR kamera perlu HTTPS + izin kamera.
- Tandai hilang pakai window.prompt/confirm (dialog browser).

## Backlog
- P2: Reservasi buku online dari portal siswa
- P2: Notifikasi pengingat kembali
- P2: Pecah App.js lebih lanjut (Books/Members/Reports/Circulation ke components/)

### 15 Okt 2026 — Pengunjung: cari nama & kamera HP
- Kolom "Nama siswa / kode kartu / NIS": ketik nama → saran anggota (GET /api/visits/member-search?q=, maks 8, ada tanda Catat masuk/keluar). Klik / panah + Enter untuk mencatat. Kode/NIS + Enter tetap bisa.
- Kolom "Cari nama pengunjung..." menyaring daftar pengunjung (nama, kelas, asal, NIS).
- Kamera (lib/camera.js): kamera belakang otomatis, kotak pindai responsif, tiap kamera punya elemen sendiri (perbaikan error "play() interrupted" / kamera dobel), berhenti aman. Setelah scan: layar hijau BERHASIL + nama, bunyi + getar, jeda 1 detik lalu siap scan berikutnya. Kartu yang sama diabaikan 5 detik. Input tidak difokuskan saat kamera aktif (keyboard HP tidak menutupi kamera). QRScanner sirkulasi memakai helper yang sama.

### 15 Okt 2026 — Gelar admin & template Excel
- Nama admin → "Devi Latifa, S.I.Pust" (konstanta ADMIN_NAME; migrasi sekali via meta `admin-title-v1`, termasuk catatan petugas lama).
- Impor anggota: template CSV diganti template Excel (GET /api/members/import-template.xlsx: lembar Anggota + Petunjuk, NIS format teks). UI hanya menerima .xlsx; NIS angka tidak jadi "24100.0"; baris judul sebelum kolom "nama" dilewati; .xls lama ditolak dengan pesan jelas.

### 15 Okt 2026 — Foto otomatis diperkecil
- `frontend/src/lib/image.js` optimizeImage(file, kind): foto anggota maks 900px, sampul 1000px, logo 600px (logo transparan tetap PNG). Perkecil bertahap + smoothing "high", JPEG 0.92 (turun ke 0.84 hanya bila perlu, target ±350/400/300 KB). Gambar yang sudah kecil tidak diubah. Input hingga 25 MB, rotasi EXIF HP ikut benar.
- PhotoBox (Shared.js) dipakai di semua unggahan (anggota, portal siswa, buku, buku masuk, logo kartu) dan menampilkan "Diperkecil otomatis X → Y · W×H px". Batas 900KB lama dihapus.

### 15 Okt 2026 — Potong & geser foto anggota
- `components/PhotoCropper.js` (react-easy-crop, portal ke body): rasio 6:7 sesuai kotak foto kartu, geser (drag/1 jari), zoom (slider/tombol/cubit/scroll 1–4×), putar 90°, atur ulang, panduan oval wajah. Escape hanya menutup jendela potong. Layar penuh di HP.
- Hasil 600×700px JPEG kualitas tinggi (≤300KB); foto kecil tidak diperbesar. Salinan kerja maks 1800px (lancar di HP). Tombol "Potong / geser" untuk mengatur ulang dari foto asli.
- Berlaku untuk semua "Foto anggota" (tambah/edit anggota admin, portal siswa). Sampul & logo tetap hanya diperkecil otomatis.

### 15 Okt 2026 — Aktif/nonaktif unggah foto siswa
- Pengaturan disimpan di `settings` id `student_photo`: enabled, until (tutup otomatis, ISO UTC), allow_replace. GET/PUT /api/settings/student-photo (PUT staff only). Respon menyertakan `open` (aktif & belum lewat batas waktu).
- Penjagaan backend: POST /members/{id}/photo & /account/photo oleh siswa ditolak 403 bila ditutup, atau bila foto sudah ada dan penggantian tidak diizinkan. Admin/petugas selalu boleh.
- UI admin: tombol "Foto siswa: Aktif/Nonaktif" di toolbar Anggota → modal switch, tutup otomatis (1 jam/2 jam/14:00/tanpa batas), centang "boleh mengganti foto". Portal siswa: tombol berubah "Unggah foto ditutup" (kunci), pemberitahuan bila foto sudah ada & tidak boleh diganti. Status dicek ulang tiap 60 detik.

### 15 Okt 2026 — Siap deploy (domain perpusmansa.vercel.app)
- Deployment check PASS. Migrasi lama di startup kini sekali jalan (meta `legacy-migrations-v1`); normalize_books tidak lagi otomatis saat start (hanya saat restore cadangan format lama). Buku contoh langsung format stok.
- CORS: FRONTEND_URL + CORS_ORIGINS (opsional) + regex emergentagent.com / emergent.host / *.vercel.app. load_dotenv(override=False). Indeks Mongo dibuat saat start.
- Statistik pengunjung disaring di database per periode (lebih cepat). .gitignore tidak lagi mengabaikan .env & test_credentials.md.
- Catatan: preview DB sempat di-reset oleh sesi tes (tombol reset data admin); data contoh sudah dipulihkan.

### 17 Okt 2026 — Impor dari GitHub (commit 9d06b02) & perbaikan merge
- Kode diambil dari github.com/devilatifa-dl/perpus (main, commit 9d06b02). Commit tersebut rusak: merge PR #3 (fitur/laporan-kartu-belakang-cetak-duplex ↔ main) meninggalkan sisa penanda konflik, dan edit manual setelahnya mengubah Modal di Shared.js (isOpen/onClose) sehingga semua modal tidak tampil.
- Merge diulang dengan benar: lib.js & QRScanner.js (fitur), Visitors.js, PhotoCropper.js, MemberImport.js (main), Shared.js (PhotoBox gabungan: foto anggota → potong lalu unggah ke object storage; sampul/logo → diperkecil otomatis di browser), StudentPortal.js (gabungan akun anggota + pengaturan foto siswa), App.js (versi fitur + tombol StudentPhotoSwitch), server.py (seed ADMIN_NAME, migrasi sekali jalan, init_storage + ensure_indexes, rute template ganda dihapus, _cell_text).
- Env baru di backend/.env: JWT_SECRET, EMERGENT_LLM_KEY, FRONTEND_URL. frontend/.yarnrc `ignore-engines true` (package.json meminta Node 22, lingkungan Node 20).
- Perbaikan ini BELUM di-push ke GitHub.

### 17 Okt 2026 — Cadangan + semua laporan
- GET /api/admin/backup.zip (admin): ZIP berisi data-cadangan.json (untuk pulihkan) + laporan/ (Excel & PDF semua periode): 01 Transaksi, 02 Buku Masuk, 03 Buku Hilang, 04 Pengunjung, 05 Peringkat Rajin Berkunjung per bulan, + BACA-SAYA.txt. Laporan hanya dibuat saat klik "Unduh cadangan".
- POST /api/admin/restore menerima ZIP tersebut atau .json lama. Batas baris ekspor laporan dinaikkan ke 100.000.

### 17 Okt 2026 — Chip "Foto siswa" dihapus
- PhotoUploadChip (chip kecil di bawah "x anggota terdaftar") dihapus. Tombol "Foto siswa" di toolbar (StudentPhotoSwitch, settings id=student_photo) jadi satu-satunya pengatur izin unggah foto siswa: media.photo_upload_allowed, StudentPortal & StudentProfile kini hanya mengikuti pengaturan ini (flag lama member_photo_upload tidak dipakai lagi).

### 17 Okt 2026 — Tampilan baru "modern · terang · ungu"
- Theme.css (dimuat terakhir di App.js): font Plus Jakarta Sans, sidebar putih dengan menu aktif ungu, banner/hero gradasi ungu, kartu & panel membulat, tombol/input/tab ungu, pemilih portal terang, login dengan lapisan ungu, portal siswa ungu.
- Warna biru/hijau-portal di CSS lama & warna grafik diganti ungu. Desain kartu anggota (Card.css) TIDAK diubah.
- HP: latar gelap di belakang menu samping (ketuk untuk menutup).
- Belum di-push ke GitHub.
- Sudah dikirim sebagai PR #4 (branch fitur/tampilan-ungu-modern).

### 17 Okt 2026 — Mode gelap ungu
- Tombol mode gelap/terang (ThemeToggle, ikon bulan/matahari) di semua halaman: pemilih portal & login (mengambang kanan atas), topbar admin/petugas, header portal siswa.
- Awal buka mengikuti pengaturan HP/komputer; pilihan manual disimpan di localStorage `perpus-theme` (src/theme.js). Skrip kecil di public/index.html mencegah kedipan putih.
- Dark.css = token & penyesuaian manual; DarkAuto.css = override warna otomatis hasil `python3 scripts/gen_dark_css.py` (jalankan ulang jika CSS lain diubah). Hanya berlaku di layar; cetak/PDF dan desain kartu anggota tetap.

### 29 Okt 2026 — Pemulihan dari ZIP "perpus-main" ke workspace baru
- Source asli disalin apa adanya (backend, frontend/src, public, plugins, package.json, yarn.lock, .yarnrc, memory, plan, scripts). Tidak ada fitur/desain yang diubah.
- Dependensi: `pip install -r requirements.txt`, `yarn install`.
- backend/.env ditambah: JWT_SECRET (baru, acak → sesi login lama tidak berlaku), EMERGENT_LLM_KEY (object storage foto), EMERGENT_EMAIL_KEY + EMAIL_FROM_NAME (email kode verifikasi), RESET_VERIFY_EMAIL=latifadevii@gmail.com, FRONTEND_URL=preview URL.
- Tidak ada di ZIP: file .env, isi database, foto anggota lama di object storage. DB baru di-seed otomatis (akun + data contoh). Data asli menunggu file cadangan dari user (Akun → Unduh cadangan di aplikasi lama → Pulihkan data).
- Regresi (testing agent iteration_1): backend 36/36 lulus, UI lengkap berfungsi.

### 29 Okt 2026 — Orientasi cetak laporan (Potret / Lanskap)
- Di setiap tab Laporan ada pilihan "Potret | Lanskap" di samping tombol Cetak (`OrientationToggle` di ReportPrint.js, disimpan di localStorage `perpus-print-orientation`, bawaan Potret).
- Cetak: @page A4 sesuai pilihan; sebelum dialog cetak, area laporan diatur selebar kertas (186 mm / 273 mm) supaya grafik digambar ulang & teks tabel dibungkus. Potret = susunan menurun (grafik 1 kolom, kartu 3/2 kolom, huruf lebih kecil); Lanskap = menyamping (grafik 2 kolom, kartu 4/5 kolom).
- PDF & Excel ikut pilihan: `orientation=portrait|landscape` di /api/reports/export.pdf|xlsx (lebar kolom PDF diskalakan ke lebar halaman; Excel page_setup A4 + pas 1 halaman lebar). Tanpa parameter = lanskap (cadangan ZIP tetap sama).

### 29 Okt 2026 — Keperluan saat scan masuk pengunjung
- Kios Pengunjung: pilihan "Keperluan masuk" (Membaca / Meminjam-mengembalikan buku / Mengerjakan tugas / Lainnya), diingat di localStorage `perpus-visit-purpose`, dikirim di POST /api/visits/scan {code, purpose} untuk setiap scan masuk (kamera, alat pemindai, ketik NIS, atau pilih nama).
- Hasil scan (panel & layar hijau kamera) menampilkan keperluan. Daftar pengunjung punya kolom KEPERLUAN yang bisa diubah (PATCH /api/visits/{id}/purpose, staff only).
- Laporan → Pengunjung kini punya kolom KEPERLUAN (layar); PDF/Excel sudah memuat Keperluan.

### 29 Okt 2026 — Keperluan "Lainnya" diketik, kelas di laporan transaksi, Excel ringkasan
- Pengunjung: chip "Lainnya" memunculkan kolom ketik keperluan (diingat di localStorage `perpus-visit-purpose-other`); teks itu yang disimpan (kosong = "Lainnya"). Form tamu juga punya kolom ketik saat pilih Lainnya. Di daftar pengunjung pilihan "Tulis sendiri..." membuka jendela untuk mengetik keperluan.
- Laporan Transaksi: kolom KELAS (layar, PDF, Excel). Transaksi baru menyimpan `class_name` saat itu; transaksi lama memakai kelas anggota sekarang (`attach_class`).
- Ringkasan & grafik: tombol Excel kini mengunduh .xlsx asli dari GET /api/reports/summary.xlsx?start&end&group&orientation (lembar Ringkasan, Grafik + 2 grafik Excel, Buku terpopuler, Anggota aktif; kop berlogo; orientasi cetak ikut pilihan Potret/Lanskap). CSV dihapus.

### 29 Okt 2026 — PDF Ringkasan & grafik
- Tombol "PDF" (ro-export-pdf) di tab Ringkasan & grafik → GET /api/reports/summary.pdf?start&end&group&orientation (reportlab, `render_summary_pdf` di summary.py; helper bersama di reportlab_helpers.py). Isi: kop berlogo, periode, kartu angka, grafik batang sirkulasi + grafik garis pengunjung, buku terpopuler, anggota aktif (dengan kelas), tanda tangan. Potret = grafik bertumpuk; lanskap = grafik & tabel berdampingan.
- Grafik layar memakai initialDimension (tanpa peringatan width/height -1).
- Belum di-push ke GitHub: user perlu memakai tombol "Save to GitHub" (repo devilatifa-dl/perpus, branch main).

### 29 Okt 2026 — Pull Request #14 ke GitHub
- Semua perubahan sesi ini di-push ke branch `fitur/orientasi-cetak-keperluan-ringkasan-pdf` dan dibuat PR #14 (base main): https://github.com/devilatifa-dl/perpus/pull/14
- Token GitHub disimpan sebagai secret `GITHUB_TOKEN` + /root/.github_token & /root/.git-credentials (chmod 600). File .env tidak di-commit.

### 29 Okt 2026 — Penanda anggota belum upload foto
- Anggota (MemberClassList): chip "Semua anggota" / "Belum foto (N)", ringkasan "N belum upload foto", lencana per kelas "X belum foto" / "Foto lengkap", tag "Belum upload foto" + avatar bergaris di baris anggota; yang belum berfoto diurutkan paling atas.
- Disimpan langsung ke branch main GitHub.

### 30 Okt 2026 — Pemulihan dari backup ZIP
- Source asli dipulihkan ke /app (backend, frontend, scripts, tests). Dependensi dipasang (pip, yarn).
- .env backend baru: JWT_SECRET baru, MONGO_URL/DB_NAME lokal, EMERGENT_LLM_KEY (object storage), FRONTEND_URL, EMAIL_FROM_NAME, RESET_VERIFY_EMAIL.
- EMERGENT_EMAIL_KEY belum ada: fitur kode reset/pulihkan data via email mengembalikan 503 dengan pesan yang jelas.
- Uji regresi: 29/29 lulus (backend + UI).

### 30 Okt 2026 — Round 2: email verifikasi & rapikan tes
- Email kode verifikasi reset/pulihkan data aktif via Emergent-managed email (Resend). EMERGENT_EMAIL_KEY di .env, penerima RESET_VERIFY_EMAIL=latifadevii@gmail.com. Hanya admin (petugas 403). Rate limit 60 dtk kini atomik (klaim sent_at sebelum kirim, dikembalikan bila gagal).
- "Kirim ulang kode" tidak lagi menampilkan dialog konfirmasi lagi.
- Tes lama diperbarui sesuai perilaku sekarang (stok per judul, portal login, nama petugas/admin, header Excel, batas terlambat 3 hari, saklar foto student-photo). tests/conftest.py: URL otomatis dari frontend/.env, reset rate-limit login per tes, hapus buku sementara RSV_. Tes reservasi pakai buku sendiri (aman di xdist).
- Hasil: 187 lulus, 4 dilewati (opt-in: RUN_DESTRUCTIVE=1 pytest -n 0 tests/test_reset_code.py; RUN_REAL_EMAIL=1 untuk tes kirim email nyata).


### 30 Okt 2026 — Round 3
- Teks "Tanpa denda, budaya membaca" dihapus dari kop PDF laporan (reports_pdf.py & summary.py).
- Kolom Kode buku dihapus dari PDF/Excel: transaksi, buku hilang, dan buku terpopuler (ringkasan PDF & Excel). Saat cetak browser, kode buku di tabel laporan & buku terpopuler disembunyikan (class print-hide-code); di layar tetap tampil.

### 30 Okt 2026 — Bersihkan data tes
- Data latihan tes dihapus (scripts/cleanup_test_data.py; data seed asli BK-1042..1045, MB-2024001..003, R-01..03, TRX-001/002, 3 akun tetap). Cadangan sebelum bersih: /root/db_backups/before_cleanup_0651 (mongodump).
- tests/conftest.py: snapshot seluruh DB saat sesi pytest mulai (proses utama xdist) dan dikembalikan persis saat selesai, jadi tes tidak meninggalkan data.

### 30 Okt 2026 — Round 4: Peringkat rajin meminjam
- Tab baru Laporan → "Peringkat rajin meminjam" (LoanLeaderboard.js), mirip peringkat rajin berkunjung: pilih bulan, podium 3 besar, 10 besar siswa (jumlah pinjam, judul berbeda, %), peringkat kelas, Cetak/PDF/Excel.
- Backend: GET /api/reports/loan-leaderboard?month=YYYY-MM (staf saja), export type=peminjam (PDF/Excel + tabel peringkat kelas), cadangan ZIP berisi 06-Peringkat-Rajin-Meminjam per bulan. Kelas memakai kelas anggota saat ini (sama untuk baris siswa & agregat kelas).
- Catatan: pemulihan DB oleh conftest hanya terjadi jika sesi pytest selesai normal (jangan dihentikan paksa; kalau terjadi, jalankan scripts/cleanup_test_data.py).

### 30 Okt 2026 — Round 5
- Pilihan orientasi kertas Potret/Lanskap dihapus dari laporan. Cetak, PDF, dan Excel (laporan & ringkasan) selalu A4 potret; parameter `orientation` di API dihapus dan nama file tanpa akhiran potret/lanskap.
- Fitur cetak kartu per kelas dihapus: tombol "Cetak kartu" di tiap kelas (daftar anggota). (Pilihan Kelas di Cetak massal sempat dihapus, lalu dikembalikan di Round 6.)

### 30 Okt 2026 — Round 6

### 30 Okt 2026 — Round 7: Build produksi / Vercel
- `CI=true yarn build` sebelumnya gagal (5 peringatan react-hooks/exhaustive-deps dianggap error). Diperbaiki dengan `eslint-disable-next-line` beralasan pada 5 efek yang sengaja (tanpa ubah perilaku). Build kini lulus.
- Ditambah `frontend/vercel.json`: framework create-react-app, build `yarn build`, output `build`, rewrite SPA semua path → /index.html (untuk /admin, /siswa). `frontend/yarn.lock` belum ter-track git — perlu ikut di-commit agar versi dependensi Vercel sama. `backend/.env`/`frontend/.env` belum di-.gitignore dan berisi rahasia — jangan di-commit.
- Vercel: Root Directory `frontend`, Node 22.x, env `REACT_APP_BACKEND_URL` = URL backend (tanpa /api, tanpa garis miring akhir). Backend FastAPI tidak berjalan di Vercel; harus di-host terpisah dan `FRONTEND_URL`/CORS diarahkan ke domain Vercel.
- Health check deployment: tanpa blocker (hanya saran optimasi query/paginasi).

- Pilihan Kelas (Semua kelas / per kelas) di Cetak massal kartu anggota dikembalikan seperti semula. Tombol "Cetak kartu" per kelas di daftar Anggota tetap dihapus.


