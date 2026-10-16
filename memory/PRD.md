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

### 15 Okt 2026 — Siap deploy (domain .my.id)
- Deployment check PASS. Migrasi lama di startup kini sekali jalan (meta `legacy-migrations-v1`); normalize_books tidak lagi otomatis saat start (hanya saat restore cadangan format lama). Buku contoh langsung format stok.
- CORS: FRONTEND_URL + CORS_ORIGINS (opsional) + regex emergentagent.com / emergent.host / *.my.id. load_dotenv(override=False). Indeks Mongo dibuat saat start.
- Statistik pengunjung disaring di database per periode (lebih cepat). .gitignore tidak lagi mengabaikan .env & test_credentials.md.
- Catatan: preview DB sempat di-reset oleh sesi tes (tombol reset data admin); data contoh sudah dipulihkan.
