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

## Tech stack
Backend FastAPI + MongoDB (motor). Frontend React + react-router-dom + Tailwind (preflight) + CSS kustom (App.css, Card.css, Portal.css). QR: html5-qrcode; QR gen: api.qrserver.com.

## Known constraints
- Foto/logo disimpan base64 di MongoDB (maks 900KB).
- QR kamera perlu HTTPS + izin kamera.
- Tandai hilang pakai window.prompt/confirm (dialog browser).

## Backlog
- P2: Reservasi buku online dari portal siswa
- P2: Notifikasi pengingat kembali
- P2: Pecah App.js lebih lanjut (Books/Members/Reports/Circulation ke components/)
