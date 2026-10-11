# PRD — Perpustakaan SMA 1 Negeri Abung Tengah

## Problem statement (original)
Web perpustakaan sekolah dengan design modern & keren untuk SMA 1 NEGERI ABUNG TENGAH (Jln Raya Subik, Desa Pekurun Selatan). Fitur: tambah/hapus buku, tambah/cetak anggota, kartu anggota digital, scan QR untuk pinjam/kembalikan, laporan buku masuk & hilang, laporan harian & bulanan, susunan rak, tanpa denda. 3 peran: admin, petugas, siswa.

## Users
- Admin: akses penuh (buku, anggota, laporan, sirkulasi)
- Petugas: operasional (buku, anggota, sirkulasi, laporan)
- Siswa: baca-saja (katalog, kartu anggota)

## Implemented (11 Oktober 2026)
- Auth JWT dengan cookie httpOnly + rate limiting
- CRUD Buku dengan foto sampul (base64 upload)
- CRUD Anggota dengan foto profil (base64 upload)
- Kartu anggota digital dengan QR Code (api.qrserver.com) + cetak
- QR Scanner kamera (html5-qrcode) + input manual kode untuk pinjam/kembali
- Susunan rak dengan progress bar kapasitas & preview sampul buku
- Laporan Transaksi/Buku Masuk/Buku Hilang + filter harian/bulanan + cetak
- Dashboard dengan statistik dan aktivitas terbaru
- Role-based gating (siswa tidak bisa tambah buku/anggota)
- Tanpa denda - konsep budaya membaca

## Tech stack
Backend FastAPI + MongoDB (motor async). Frontend React + Tailwind. QR: html5-qrcode. QR gen: api.qrserver.com.

## Known constraints
- Foto disimpan sebagai base64 di MongoDB (MVP, maks 900KB per gambar)
- QR scan kamera memerlukan HTTPS + izin kamera browser
- Laporan "Buku Masuk" dan "Buku Hilang" masih seeded sample (perlu CRUD terpisah)

## Backlog
- P1: CRUD endpoint untuk Buku Masuk & Buku Hilang (saat ini sample)
- P1: Export laporan ke Excel/PDF
- P2: Reservasi buku online
- P2: Notifikasi pengingat kembali
- P2: Multi-cabang / multi-sekolah
