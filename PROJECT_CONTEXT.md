# PROJECT_CONTEXT — Perpustakaan SMA Negeri 1 Abung Tengah ("Ruang Baca SMANSA")

Dibuat 1 Nov 2026 dari isi workspace yang benar-benar ada. Detail riwayat lengkap: `memory/PRD.md`.

## 1. Fungsi aplikasi
Web perpustakaan sekolah (Jln Raya Subik, Desa Pekurun Selatan, Abung Tengah, Lampung Utara; NPSN 69948538).
- `/` pemilih portal · `/admin` Admin & Petugas (akses penuh) · `/siswa` Siswa (hanya lihat katalog & rak).
- Tanpa denda. Login JWT (cookie httpOnly / Bearer), 3 peran: admin, petugas, siswa.

## 2. Teknologi
- **Backend:** Python FastAPI + MongoDB (motor), reportlab (PDF), openpyxl (Excel), bcrypt, PyJWT. File utama `backend/server.py` + modul `visits.py`, `summary.py`, `loan_rank.py`, `reports_pdf.py`, `restore_big.py`, `purge.py`, `media.py`, `mailer.py`. Semua route berawalan `/api`.
- **Frontend:** React (CRA + craco), react-router-dom, Tailwind + CSS kustom (App.css, Glass.css, Dark*.css, Ops.css, dll), lucide-react, html5-qrcode, recharts. Paket: **yarn** (jangan npm).
- QR dibuat lewat api.qrserver.com.

## 3. Fitur yang sudah dibuat (ringkas)
- Koleksi buku: tambah/edit/hapus, sampul, stok per eksemplar (satu judul = satu QR), buku masuk, lapor hilang/ditemukan, cetak QR massal, stock opname, rak & kapasitas.
- Anggota: tambah/edit, foto (potong/geser, object storage), kartu anggota digital depan/belakang + desainer kartu, cetak massal, impor Excel (template), **impor kenaikan kelas** (NIS terdaftar → hanya kelas diperbarui, ID/QR tetap, NIS tidak boleh ganda, daftar anggota yang tidak ada di berkas), naik kelas massal, akun siswa.
- Sirkulasi: scan QR kamera / manual pinjam & kembali, reservasi, pengingat terlambat.
- Pengunjung: scan masuk/keluar, tamu, keperluan, auto keluar, statistik & persentase per kelas.
- Laporan: ringkasan & grafik, transaksi, buku masuk, buku hilang, pengunjung, statistik, peringkat rajin berkunjung & **Rajin Peminjaman**; cetak A4, PDF, Excel. Kelas di laporan = kelas saat transaksi terjadi.
- **Hapus laporan** (admin): transaksi/pengunjung/buku masuk/buku hilang — centang baris, per tahun, atau rentang tanggal; pilihan **Hapus** (konfirmasi) atau **Unduh Excel**; pinjaman aktif & pengunjung di dalam dilindungi; log di koleksi `purge_logs`. Tanpa kode email.
- Cadangan data (JSON/ZIP) & **Pulihkan data** (unggah bertahap, tanpa kode email). Reset data masih pakai kode email.
- Mode gelap ungu, tampilan glass modern.

## 4. Struktur proyek
```
backend/            FastAPI (server.py + modul), assets/ (logo PDF), tests/, requirements.txt, .env.example
frontend/           React app: src/App.js, src/components/*, src/*.css, public/, package.json, yarn.lock, .env.example
memory/             PRD.md (riwayat fitur), PROMPT_BACKUP.md
scripts/            utilitas (push_to_github.sh, gen_dark_css.py, dll)
tests/, test_reports/  hasil uji agen
plan/, design_guidelines.*, README.md, vercel.json
```

## 5. Integrasi
| Integrasi | Dipakai untuk | Env var |
|---|---|---|
| Emergent Object Storage (Universal Key) | foto anggota | `EMERGENT_LLM_KEY` |
| Emergent Managed Email (Resend) | kode verifikasi Reset data | `EMERGENT_EMAIL_KEY`, `EMAIL_FROM_NAME`, `RESET_VERIFY_EMAIL` |
| api.qrserver.com | gambar QR | – |
Kunci diambil dari platform Emergent; nilainya TIDAK disertakan di backup.

## 6. Database (MongoDB)
- Koneksi via `MONGO_URL`, nama DB via `DB_NAME` (env, jangan hardcode). Preview workspace: MongoDB lokal `mongodb://localhost:27017`, DB `test_database`.
- Koleksi: `users, members, books, shelves, transactions, reservations, incoming, missing, visits, settings, stocktake, files, meta, login_attempts, reset_codes, restore_uploads, restore_chunks, purge_logs`. ID memakai string/UUID, bukan ObjectId.
- Data TIDAK ada di ZIP/GitHub. Pindahkan data lewat aplikasi: **Akun & sandi → Unduh cadangan** di server lama, lalu **Pulihkan data** di server baru.
- Saat DB kosong, akun contoh & data contoh dibuat otomatis (lihat seed di `server.py`). Ganti sandi akun bawaan di produksi.

## 7. Deployment
- **Frontend produksi:** Vercel — https://perpusmansa.vercel.app (`vercel.json`: build `frontend`, `/api/*` diteruskan ke backend produksi).
- **Backend produksi:** Emergent deployment `https://library-devilatifa.emergent.host` (tujuan rewrite di `vercel.json`).
- **Railway:** tidak ada konfigurasi Railway di repo/workspace ini. Jika ingin pindah ke Railway: buat service Python (start: `uvicorn server:app --host 0.0.0.0 --port $PORT`, root `backend/`), tambah MongoDB (Railway plugin / MongoDB Atlas), isi env sesuai `backend/.env.example`, lalu ubah tujuan rewrite `/api` di `vercel.json` ke URL Railway.

## 8. Status pekerjaan (1 Nov 2026)
- Semua fitur di atas berjalan di preview dan lolos uji agen (iteration_19 & 20).
- Perubahan sesi 1 Nov 2026 **belum** ada di GitHub — simpan lewat tombol "Save to GitHub" (branch baru) lalu buat PR (PR terakhir di repo: #15).
- Backlog: denda opsional, notifikasi jatuh tempo, laporan bulanan otomatis, riwayat penghapusan di UI.

## 9. Melanjutkan di workspace baru
1. Ekstrak `project-backup.zip` ke `/app` (jangan timpa `.env` bawaan workspace) atau ambil dari GitHub.
2. `pip install -r backend/requirements.txt` dan `cd frontend && yarn install`.
3. Lengkapi `backend/.env` sesuai `backend/.env.example` (JWT_SECRET baru, EMERGENT_LLM_KEY, EMERGENT_EMAIL_KEY dari platform), `frontend/.env` sesuai `frontend/.env.example`.
4. `sudo supervisorctl restart backend frontend`, cek `POST /api/auth/login`.
5. Pulihkan data dari file cadangan lewat menu Akun & sandi → Pulihkan data.
