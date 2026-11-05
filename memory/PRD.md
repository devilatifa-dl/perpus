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

## GitHub sync (workspace)
- Token: `GITHUB_TOKEN` in backend/.env (secure card). Never print it.
- Push: `bash /app/scripts/push_to_github.sh --dry-run <branch>` then `bash /app/scripts/push_to_github.sh <branch> "pesan"`.
- Uses separate clone at /root/perpus-github (workspace /app git history is unrelated to GitHub). Excludes .env/node_modules/build; aborts if secrets detected.
- Pushing to `main` triggers Vercel redeploy (perpusmansa.vercel.app) — confirm with user first.

## 2026-10-30 changes
- Removed Potret/Lanskap orientation toggle from Laporan (print always A4 portrait; downloads use backend default orientation).
- Removed per-class "Cetak kartu" button on Anggota class rows (MemberClassList). Kept "Cetak massal" (BulkCardPrint with class select) and single-card print.
- New "Peringkat rajin meminjam": backend/loan_rank.py GET /api/loans/leaderboard?month=YYYY-MM (counts action=pinjam per WIB month; students loans/books/days, classes). Export type `peringkat-pinjam` (PDF/Excel). Admin Laporan tab `peringkat-pinjam`; siswa portal Peringkat tab has switch Rajin berkunjung / Rajin meminjam.
- PDF/Excel downloads no longer show book codes (BK-xxxx): removed "Kode" column from Transaksi & Buku hilang (reports_pdf.table_rows) and from "Buku terpopuler" in summary PDF/Excel (summary.py). On-screen views unchanged.
- PDF header/meta no longer show "Tanpa denda, budaya membaca" or "A4 potret/lanskap" (reports_pdf.py, summary.py).
- PDF kop shows "NPSN: 69948538" under the address (SCHOOL_NPSN in reports_pdf.py, used by summary.py). School has no phone/email -> not shown.
- Koleksi buku: "Cetak QR massal" (components/BulkBookQrPrint.js, BookQr.css; qrcode.react offline SVG). Semua buku / pilih per buku, filter rak, 1 label per judul atau sesuai eksemplar, opsi tampilkan kode; 24 label per A4. QR modal per buku punya tombol cetak sesuai eksemplar.
- Pulihkan data tanpa batas ukuran: backend/restore_big.py (start/chunk/finish/status, chunk 8MB disimpan di Mongo restore_chunks, streaming ijson -> koleksi _restore_tmp_* -> $out, data lama aman bila gagal). /admin/restore lama tetap ada tanpa batas. Frontend AccountManager: unggah bertahap + progress. Hosting emergent.host menolak unggahan tunggal >~100MB (413) -> karena itu dipotong.

### 1 Nov 2026 — Impor kenaikan kelas
- POST /api/members/import: NIS sudah terdaftar → hanya kelas diperbarui (ID/QR tetap, nama tidak diubah); NIS ganda dalam berkas ditolak; respons + `updated`, `unchanged`, `class_changes`, `not_in_file` (anggota terdaftar yang tidak ada di berkas, tidak diubah).
- NIS unik juga di tambah/edit anggota (`ensure_unique_nis`).
- `freeze_old_class`: sebelum kelas diganti (impor/promote/edit), transaksi & kunjungan lama tanpa kelas dikunci ke kelas lama → laporan memakai kelas saat transaksi terjadi. Akun siswa ikut kelas baru.
- 1 Nov 2026: Laporan Pengunjung PDF/Excel tanpa kolom Jenis & Cara keluar; cetak langsung (kelas .print-hide) sembunyikan kolom Cara keluar + teks "Anggota · NIS"; cetak Transaksi sembunyikan kode buku. Label peringkat "Rajin Peminjaman".
- 1 Nov 2026: Hapus laporan (backend/purge.py, components/ReportPurge.js): admin + kode email (purpose "purge"); transaksi/kunjungan/masuk/hilang; mode terpilih (checkbox)/tahun/rentang; cadangan Excel otomatis; pinjaman aktif & pengunjung di dalam dilindungi; log di purge_logs.
- 1 Nov 2026: Hapus 1-5 data tanpa kode email (NO_CODE_MAX=5, preview.needs_code); tombol "Unduh cadangan Excel saja" tanpa kode.
- 1 Nov 2026: Kode email DIHAPUS untuk hapus laporan & pulihkan data (keputusan user: terlalu ribet). Modal hapus: tombol "Hapus N data" (window.confirm) + "Unduh Excel". Reset data masih pakai kode email.

## 3 Nov 2026
- PWA: service-worker.js (cache halaman, aset, data API GET network-first), manifest.json + ikon, banner offline/online, kartu pasang aplikasi, cache API dibersihkan saat login/keluar. Lolos uji iteration_21.
- Teks "Rajin Peminjaman" diganti "Rajin meminjam" (tab laporan, tombol peringkat, judul PDF).
- Sisa fungsi kode verifikasi email (verify_reset_code) dihapus; Reset/Pulihkan/Hapus laporan cukup konfirmasi di aplikasi.
- Pulihkan data: ZIP terpotong (unduhan tidak selesai) kini diselamatkan lewat local header bila data-cadangan.json masih utuh; pesan error jelas bila JSON ikut terpotong; status mengembalikan salvaged. Unduh cadangan memeriksa keutuhan ZIP (X-Backup-Bytes + tanda EOCD); tombol baru "Unduh data saja (.json)".
- Cadangan ZIP kini berisi laporan/06-Peringkat-Rajin-Meminjam per bulan (PDF + Excel). Lolos uji iteration_22.
- Catatan: koleksi files (foto anggota) belum ikut cadangan.
- Satu tombol "Unduh cadangan": ZIP lengkap dengan cek keutuhan, coba ulang 1x, lalu otomatis simpan data-cadangan.json bila ZIP gagal.
- Lebih cepat di HP: /api/books 24,6 MB -> 35 KB (sampul base64 diganti URL /api/books/{id}/cover?v=&s=thumb|full, thumbnail JPEG ~25 KB, cache permanen via SW v2); GZip untuk JSON; halaman admin/siswa/grafik/kamera dimuat terpisah (Root.js, styles.js); font tidak menahan tampilan; layar pembuka di index.html; gambar loading=lazy. Lolos uji iteration_23.

## 4 Nov 2026 — Pemulihan dari ZIP "perpus-main (2)" ke workspace baru
- Source asli disalin apa adanya (backend, frontend src/public/plugins, package.json, yarn.lock, .yarnrc, docs, memory, plan, scripts, deployer-agent-docs). Tidak ada fitur/desain yang diubah.
- pip install -r requirements.txt, yarn install. backend/.env ditambah JWT_SECRET (baru) + FRONTEND_URL (preview).
- Tidak ada di ZIP: .env, isi database, .env.example (disebut di PROJECT_CONTEXT tapi tidak ada), mailer.py (disebut tapi tidak dipakai lagi). Foto kini di MongoDB (koleksi files) → tidak butuh EMERGENT_LLM_KEY; kode email sudah dihapus → tidak butuh EMERGENT_EMAIL_KEY. GITHUB_TOKEN belum ada (hanya untuk scripts/push_to_github.sh).
- Folder root tests/, test_reports/ lama & backend_test*.py root tidak disalin (folder dikunci sistem uji workspace).
- DB baru di-seed otomatis (akun + data contoh). Regresi iteration_1: backend 23/23, UI semua alur lulus.

## 4 Nov 2026 — Siap hosting eksternal (Vercel / Render)
- CORS dari env: FRONTEND_URL + CORS_ORIGINS ("*" = semua) + CORS_ORIGIN_REGEX; regex Emergent/Vercel yang ditanam dihapus.
- backend/.env.example & frontend/.env.example terdokumentasi; backend/requirements.prod.txt (paket runtime saja, diuji di venv bersih).
- Vercel: middleware.js (root) proxy /api/* → env BACKEND_URL; vercel.json tanpa URL backend, pakai yarn. Deployment perpusmansa.vercel.app WAJIB menambah env BACKEND_URL sebelum push berikutnya.
- render.yaml: perpus-backend (python) + perpus-frontend (static, rewrite /api/* → https://perpus-backend.onrender.com, sesuaikan).
- index.html: skrip Emergent (emergent-main.js, posthog) hanya dimuat di *.emergentagent.com / *.emergent.host.

## 4 Nov 2026 — .env aman & QR kartu offline
- .gitignore mengabaikan .env / .env.* (kecuali .env.example); scripts/push_to_github.sh tetap mengirim .env.example.
- QR kartu anggota (MemberCard) dibuat di browser dengan qrcode.react (QRCodeSVG), tidak lagi memanggil api.qrserver.com. QR modal buku di Koleksi masih memakai api.qrserver.com.

## 4 Nov 2026 — Notifikasi 3 detik & sandi admin untuk reset
- PwaStatus: banner "Sedang offline" & "Server lambat" hilang sendiri setelah 3 detik (banner "Kembali online" tetap).
- Reset data: modal konfirmasi (portal ke body) wajib isi sandi admin; backend /api/admin/reset-data menolak 400 bila sandi kosong/salah.
- Menu "Akun & sandi" di HP kini menutup sidebar. Lolos uji iteration_3 (jalur sandi benar tidak dijalankan agar data tidak terhapus).

## 4 Nov 2026 — Optimasi performa
- Daftar bertahap (lib/showMore.js, ShowMore): Koleksi buku & Laporan & Pengunjung 50 baris, katalog siswa 48, anggota per kelas 40; sisanya dimuat otomatis saat digulir / tombol "Muat lebih banyak". Saat cetak (beforeprint) semua baris tampil. Data tetap diambil sekaligus dari API (payload ringan); belum ada pagination server.
- Sampul buku dikompres juga di server (media.shrink_data_url: maks 1000px, ≤400KB JPEG) pada tambah/edit buku & buku masuk. Foto anggota sudah dikompres server (1080px, ≤500KB) + browser.
- Indeks Mongo diperluas (books title/author/created_at/shelf/category/status, members name/class_name, transactions date/action/compound, reservations, incoming, missing, files.storage_path, restore_chunks, users, login_attempts).
- Service worker: saat install menyimpan semua bundle ber-hash dari asset-manifest.json (halaman lazy ikut tersimpan). Lolos uji iteration_4.



- Foto anggota/sampul/logo sudah di MongoDB (tidak bergantung Emergent). README.md = panduan deploy lengkap + Atlas. Lolos uji iteration_2.



### 4 Nov 2026 — Pulihkan data asli ke preview
- Data diambil (hanya baca) dari server lama library-devilatifa.emergent.host lewat `scripts/pull_from_old_server.py` (kredensial: OLD_SERVER_ADMIN_EMAIL / OLD_SERVER_ADMIN_PASSWORD di backend/.env), lalu dipulihkan lewat POST /api/admin/restore.
- Hasil: 101 judul buku (425 eksemplar), 410 anggota, 100 transaksi, 105 pengunjung, 3 rak, pengaturan kartu. 3 foto anggota disalin ke koleksi `files` (`scripts/import_old_accounts_photos.py`).
- Akun: admin & petugas disamakan dengan server lama (sandi admin = sandi server lama; sandi petugas tetap bawaan karena sandi tidak bisa dibaca dari server lama). Server lama tidak punya akun login per siswa.
- 4 Nov 2026: Kartu anggota — baris "Kelas" disembunyikan hanya saat dicetak (CSS @media print di Card.css); tetap tampil di layar/pratinjau. Berlaku untuk cetak satu kartu, cetak massal, dan kartu di portal siswa.
- 4 Nov 2026: Kartu anggota — nama sekolah & judul kartu (KARTU ANGGOTA PERPUSTAKAAN) rata tengah di layar, desain kartu, dan cetak (Card.css).
- 4 Nov 2026: Desain kartu → grup "Teks & ukuran teks di kartu" (components/CardTextControls.js): edit nama sekolah, judul kartu, label di atas nama (card_owner_label), label Kelas/NIS (card_class_label, card_nis_label), alamat (card_address); ukuran per teks 50-200% (card_text_sizes: school,title,owner,name,fields,address,code,back_title,back_rules,back_web) via CSS var --k-* (Card.css, kelas fs-on). Backend SettingsInput menyimpan & membatasi nilai.

## 5 Nov 2026 — Pemulihan dari ZIP "perpus-main (4)" ke workspace baru
- Source asli disalin apa adanya (backend, frontend src/public/plugins/config, package.json, yarn.lock, .yarnrc, memory, plan, scripts, docs, vercel.json, render.yaml, middleware.js). .env bawaan workspace tidak ditimpa. Tidak ada fitur/desain yang diubah.
- pip install -r requirements.txt, yarn install. backend/.env ditambah JWT_SECRET (baru, acak) + FRONTEND_URL (preview).
- Tidak ada di ZIP: file .env (sengaja), isi database, GITHUB_TOKEN, OLD_SERVER_ADMIN_EMAIL/PASSWORD (hanya untuk skrip). DB baru di-seed otomatis (4 buku, 3 anggota, 3 rak, 3 akun).
- Regresi iteration_1: backend 42/43 (1 = endpoint /api/admin/reset-code yang memang sudah dihapus), UI semua halaman tampil.

## 5 Nov 2026 — Mode offline (Sirkulasi, Pengunjung, Laporan Pengunjung) + desain kartu
- IndexedDB (`frontend/src/lib/idb.js`, `lib/offline.js`): store `cache` (salinan /auth/me, /books, /members, /reports, /visits?date, /visits/history, dll via `cachedGet`) & `queue` (antrean offline: tx, visit-scan, visit-guest, visit-checkout). Saat offline atau request gagal karena jaringan → disimpan di antrean; overlay `applyPendingStaff` / `applyPendingVisits` menampilkan stok, transaksi, pinjaman & pengunjung yang belum tersinkron (tag "Menunggu sinkron").
- Sinkron otomatis: event `online` + interval 30 dtk + tombol "Sinkronkan". Urut FIFO; 4xx dari server → dibuang otomatis + toast & daftar "Dibuang saat sinkron" (keputusan user); jaringan/5xx/401/403/429 → dicoba lagi nanti.
- Backend: `client_id` (anti dobel) + `client_time` (waktu kejadian asli, maks 14 hari lalu) di POST /api/transactions, /api/visits/scan, /api/visits/guest, /api/visits/{id}/checkout (`backend/offline_sync.py`). Scan keluar offline setelah auto-keluar → jam keluar asli dipakai.
- Indikator `OfflineBar` (components/OfflineBar.js, Offline.css) di Sirkulasi, Pengunjung, Laporan → Pengunjung. Pencarian nama pengunjung offline memakai daftar anggota tersimpan.
- Service worker v3: precache /admin, /siswa, font kartu; halaman terakhir (menu admin) diingat di localStorage `perpus-admin-view`.
- Kartu anggota: font Shrikhand, Anton, Adumu Regular (Kyle Hathcoat, gratis pribadi & komersial), El Messiri (pengganti Montaser Arabic — tidak ada sumber gratis resmi; keputusan user), DM Sans — file di public/fonts (+ fonts.css). Font per teks (`card_text_fonts`), ukuran Kelas & NIS terpisah (`class`,`nis`; `fields` lama tetap dihormati), tampil/sembunyi Kelas/NIS/Kode/Alamat, foto: posisi kiri/kanan/atas, bentuk kotak/membulat/bulat, ukuran 60–160% (`card_photo_size`, `card_photo_shape`).
- Desain kartu dirapikan: 4 tab (Tampilan · Teks & font · Foto & logo · Belakang), baris ringkas (teks + font + ukuran), tombol Bawaan.
- Cetak massal: baris Kelas disembunyikan juga di pratinjau (CardDesign.css).
- Catatan: file sisa tidak terpakai /app/fonts_dl, public/fonts/Adumu-400.woff2, DMSans-700.woff2, ElMessiri-700.woff2 (tidak bisa dihapus dari sesi ini).

## Update: Kelola Antrean Offline
- Data offline yang ditolak server tidak hilang: tersimpan di perangkat (IndexedDB "rejected") dan tampil di panel status Online/Offline (Sirkulasi, Pengunjung, Laporan Kunjungan) dengan alasan penolakan.
- Aksi: Coba lagi, Hapus, Hapus semua; data menunggu sinkron bisa Dibatalkan. Hapus/batalkan pakai konfirmasi 2 klik.
- Sesi login disimpan di perangkat saat login agar aplikasi tetap bisa dibuka ulang saat offline; dihapus saat logout.
