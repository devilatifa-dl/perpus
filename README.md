# Perpustakaan SMA Negeri 1 Abung Tengah

React (frontend) + FastAPI (backend) + MongoDB. Siap jalan di workspace Emergent tanpa mengubah kode.

## Menjalankan di workspace Emergent baru (untuk agent)
Jangan ubah kode, desain, atau fitur. Cukup lakukan langkah ini:

1. Salin repo ini ke `/app` (jangan timpa `backend/.env` dan `frontend/.env` bawaan workspace).
2. Pasang dependency:
   - `pip install -r /app/backend/requirements.txt`
   - `cd /app/frontend && yarn install` (pakai yarn, bukan npm)
3. Tambahkan ke `/app/backend/.env` (jangan hapus MONGO_URL, DB_NAME, CORS_ORIGINS):
   - `JWT_SECRET` = string acak panjang
   - `EMERGENT_LLM_KEY` = Emergent LLM key (dari `emergent_integrations_manager`), dipakai untuk penyimpanan foto
   - `EMERGENT_EMAIL_KEY` = kunci Emergent Managed Resend (dari integration_expert, playbook Resend)
   - `EMAIL_FROM_NAME="Perpustakaan SMAN 1"`
   - `RESET_VERIFY_EMAIL=latifadevii@gmail.com` (penerima kode verifikasi reset & pulihkan data)
   - `FRONTEND_URL` = nilai REACT_APP_BACKEND_URL dari `/app/frontend/.env`
4. `sudo supervisorctl restart backend frontend`
5. Cek: `POST /api/auth/login` dengan akun di `memory/test_credentials.md`.

Saat database masih kosong, akun admin/petugas/siswa dan data contoh dibuat otomatis.

## Akun
Lihat `memory/test_credentials.md`.

## Data
Data (buku, anggota, transaksi) ada di database, tidak ikut tersimpan di GitHub.
Untuk memindahkan data: menu Akun → Unduh cadangan (ZIP) di tempat lama, lalu Pulihkan data di tempat baru.

## Domain
Frontend: https://perpusmansa.vercel.app. Vercel meneruskan `/api` ke server produksi (lihat `vercel.json`).
