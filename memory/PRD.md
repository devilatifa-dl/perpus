# PRD — Perpustakaan SMA 1 Negeri Abung Tengah

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
- Refactor: komponen dipecah ke `src/components/*` (Login, Shared, MemberCard, CardDesigner, MemberHistory, IncomingForm, Shelves, StudentPortal, PortalChooser) + `src/lib.js`.

## Tech stack
Backend FastAPI + MongoDB (motor). Frontend React + react-router-dom + Tailwind (preflight) + CSS kustom (App.css, Card.css, Portal.css). QR: html5-qrcode; QR gen: api.qrserver.com.

## Known constraints
- Foto/logo disimpan base64 di MongoDB (maks 900KB).
- QR kamera perlu HTTPS + izin kamera.
- Tandai hilang pakai window.prompt/confirm (dialog browser).

## Backlog
- P1: Export laporan ke Excel/PDF
- P2: Modal kustom untuk lapor hilang (ganti window.prompt)
- P2: Reservasi buku online dari portal siswa
- P2: Notifikasi pengingat kembali
