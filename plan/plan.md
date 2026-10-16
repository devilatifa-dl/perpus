# Perpus — Lanjutan Aplikasi Perpustakaan

Melanjutkan aplikasi perpustakaan sekolah dari proyek `perpus-main` yang sudah ada: memperbaiki scan QR pengunjung, mengatur izin upload foto anggota, dan menambahkan laporan & statistik.
Tampilan lama tetap dipakai. Fitur baru dibuat dengan gaya yang sama.

## Untuk siapa
- **Admin / petugas perpustakaan**: mengelola data, memindai kunjungan, mengatur izin upload foto, dan melihat laporan.
- **Anggota (siswa)**: login untuk melihat katalog, riwayat pinjam, dan profilnya, serta upload foto saat diizinkan admin.

## Fitur inti dan pengalaman
1. **Perbaikan kamera scan QR pengunjung**
   - Kamera bisa dibuka dengan benar di HP maupun laptop, termasuk izin kamera dan pilihan kamera depan/belakang.
   - QR anggota terbaca, kunjungan tercatat, lalu muncul konfirmasi nama pengunjung.
   - Jika kamera ditolak atau tidak ada, muncul pesan yang jelas dan tersedia input kode anggota secara manual.
2. **Saklar aktif/nonaktif upload foto anggota (di admin)**
   - Ada satu saklar umum yang membuka atau menutup upload foto untuk semua anggota.
   - Saat saklar mati, tombol upload di sisi anggota disembunyikan atau dikunci, dan server juga menolak upload.
   - Admin tetap bisa mengganti foto anggota kapan saja.
3. **Kompres foto otomatis**
   - Foto besar (misalnya 5–10 MB dari kamera HP) otomatis diperkecil ke ukuran yang ditentukan web, maksimal sisi terpanjang 1080 px dan hasilnya biasanya di bawah ±500 KB.
   - Kualitas tetap tajam setara HD (kompresi kualitas tinggi), dan orientasi foto diperbaiki otomatis.
   - Format yang diterima: JPG, PNG, WEBP, dan HEIC (foto iPhone).
4. **Laporan dan statistik (admin)**
   - Ringkasan: total buku, anggota, peminjaman aktif, buku terlambat, dan kunjungan hari ini.
   - Grafik peminjaman dan kunjungan per hari atau per bulan.
   - Daftar buku terpopuler dan anggota paling aktif.
   - Filter rentang tanggal, lalu ekspor ke Excel/CSV dan cetak ke PDF.
5. **Login email & password untuk admin dan anggota**
   - Setiap peran hanya melihat menunya sendiri.
   - Jika proyek sudah punya sistem login, sistem itu tetap dipakai dan dilengkapi peran anggota.

## Alur pengguna
- **Admin**: login → dashboard statistik → menu Laporan (pilih tanggal → lihat grafik → ekspor) → menu Scan Pengunjung (kamera terbuka → scan QR → kunjungan tercatat) → menu Pengaturan (nyalakan/matikan izin upload foto).
- **Anggota**: login → profil → upload foto jika izin terbuka (foto otomatis dikompres → tampil di profil) → lihat katalog dan riwayat pinjam.

## Nuansa UI/UX
- Mengikuti warna, font, dan tata letak yang sudah ada di proyek.
- Halaman laporan berisi kartu angka dan grafik yang jelas, dan tetap rapi di HP.
- Ada notifikasi singkat untuk setiap aksi, misalnya "Kunjungan tercatat", "Upload foto sedang ditutup admin", atau "Foto berhasil diunggah".

## Tahapan implementasi
- **Fase 1 (MVP, dikerjakan sekarang)**: perbaikan scan QR pengunjung, saklar izin upload foto, kompres foto otomatis dengan penyimpanan file yang aman, laporan & statistik beserta ekspor, serta login admin & anggota.
- **Fase 2**: denda keterlambatan otomatis, notifikasi jatuh tempo ke anggota, dan izin upload per anggota atau berjadwal (misalnya hanya dibuka pada tanggal tertentu).
- **Fase 3**: kartu anggota ber-QR yang bisa dicetak massal, reservasi buku oleh anggota, dan laporan bulanan otomatis.

## Asumsi
- Kode di `perpus-main.zip` akan diperiksa dulu. Fitur yang sudah berjalan (buku, anggota, peminjaman) dipertahankan dan tidak dibuat ulang.
- Saklar izin upload berlaku untuk semua anggota sekaligus, bukan per siswa.
- Batas foto: sisi terpanjang 1080 px dan kualitas tinggi. Foto yang sudah kecil tidak diperbesar.
- Foto disimpan di penyimpanan file (bukan di database). Foto hanya bisa dilihat oleh pengguna yang sudah login.
- Akun admin awal dibuat otomatis. Anggota dibuatkan akunnya oleh admin dan tidak mendaftar sendiri.
- Penyebab error scan QR baru akan dipastikan setelah kode dibuka. Perbaikan dilakukan pada penyebab utamanya, bukan sekadar menutupi error.
- Bahasa antarmuka tetap Bahasa Indonesia.
