# Panduan Deploy

Panduan lengkap (MongoDB Atlas, Render, Vercel, semua environment variable) ada di **[README.md](README.md)**.

Ringkas:
1. MongoDB Atlas (M0 gratis) → salin `MONGO_URL`.
2. Render → Blueprint dari `render.yaml` → isi `MONGO_URL`, `FRONTEND_URL`.
3. Frontend:
   - **Vercel:** import repo (root). Tanpa env apa pun, `/api/*` diteruskan ke backend produksi Emergent `https://perpus-library-7.emergent.host` (rewrite di `vercel.json`). Untuk memakai backend lain (mis. Render), isi env `BACKEND_URL` = URL backend; `middleware.js` akan memakainya.
   - **Render Static Site:** dibuat dari `render.yaml`; sesuaikan tujuan rewrite `/api/*` bila URL backend berbeda.
4. Ganti sandi akun bawaan.

> Catatan: `vercel.json` berisi backend bawaan `https://perpus-library-7.emergent.host` sehingga perpusmansa.vercel.app
> langsung tersambung tanpa env. Env `BACKEND_URL` di Vercel (opsional) menimpa backend bawaan tersebut.
