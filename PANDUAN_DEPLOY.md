# Panduan Deploy

Panduan lengkap (MongoDB Atlas, Render, Vercel, semua environment variable) ada di **[README.md](README.md)**.

Ringkas:
1. MongoDB Atlas (M0 gratis) → salin `MONGO_URL`.
2. Render → Blueprint dari `render.yaml` → isi `MONGO_URL`, `FRONTEND_URL`.
3. Frontend:
   - **Vercel:** import repo (root), isi env `BACKEND_URL` = URL backend Render. `middleware.js` meneruskan `/api/*`.
   - **Render Static Site:** dibuat dari `render.yaml`; sesuaikan tujuan rewrite `/api/*` bila URL backend berbeda.
4. Ganti sandi akun bawaan.

> Perubahan penting: `vercel.json` **tidak lagi** berisi URL backend. Untuk deployment Vercel yang sudah ada
> (perpusmansa.vercel.app), tambahkan env `BACKEND_URL` di Vercel **sebelum** push berikutnya, agar `/api` tetap tersambung.
