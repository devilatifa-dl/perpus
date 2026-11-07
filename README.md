# Ruang Baca SMANSA Ã¢â‚¬â€ Perpustakaan SMA Negeri 1 Abung Tengah

Aplikasi web perpustakaan sekolah: koleksi buku, anggota & kartu anggota (cetak massal, depan/belakang),
sirkulasi dengan scan QR, reservasi buku, pengunjung, laporan (cetak A4, PDF, Excel), cadangan/pulihkan data, PWA.

- **Backend:** Python 3.11 Ã‚Â· FastAPI Ã‚Â· MongoDB (motor) Ã‚Â· reportlab Ã‚Â· openpyxl Ã‚Â· Pillow
- **Frontend:** React (CRA + craco) Ã‚Â· Tailwind Ã‚Â· html5-qrcode Ã‚Â· recharts Ã‚Â· paket **yarn**
- Portal: `/` pemilih portal Ã‚Â· `/admin` admin & petugas Ã‚Â· `/siswa` siswa

Aplikasi ini **tidak bergantung pada layanan Emergent**:
- Semua data **termasuk foto anggota, sampul buku, dan logo** disimpan di MongoDB
  (foto anggota Ã¢â€ â€™ koleksi `files`, sampul & logo Ã¢â€ â€™ base64 di dokumen buku/pengaturan, dikecilkan otomatis).
- Semua URL dan rahasia dibaca dari environment variable. Tidak ada URL backend yang ditanam di kode.
- Skrip Emergent di `public/index.html` (editor visual & analitik) hanya dimuat bila domainnya
  `*.emergentagent.com` / `*.emergent.host`; di Vercel/Render tidak dimuat sama sekali.
- Paket `@emergentbase/*` di `package.json` hanya dipakai dev server (`yarn start`), tidak ikut di build produksi.
- Gambar QR kartu anggota memakai layanan publik `api.qrserver.com` (bukan Emergent); QR label buku dibuat offline di browser.

---

## 1. Arsitektur deploy yang disarankan

```
Browser Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€“Âº Frontend (Vercel / Render Static)  Ã¢â€â‚¬Ã¢â€â‚¬/api/*Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€“Âº  Backend FastAPI (Render Web Service)  Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€“Âº  MongoDB Atlas
            domain yang sama untuk /api (proxy)
```

Frontend **meneruskan `/api/*` ke backend di domain yang sama (proxy)**. Dengan cara ini:
login cookie tetap first-party, foto anggota (`/api/files/...`) dan sampul (`/api/books/{id}/cover`)
tampil tanpa pengaturan CORS, dan semua fitur berjalan sama persis seperti di preview.

| Platform | Cara proxy `/api` | Diatur lewat |
|---|---|---|
| Vercel | rewrite `/api/*` di `vercel.json` (bawaan: `https://perpus-backend.onrender.com`) + `middleware.js` | env **`BACKEND_URL`** di Vercel (opsional, menimpa bawaan) |
| Render Static Site | rewrite `/api/*` di `render.yaml` | `routes` di `render.yaml` / Dashboard Ã¢â€ â€™ Redirects/Rewrites |
> **Pindah dari Emergent (gratis):** lihat **[PANDUAN_PINDAH_RENDER.md](PANDUAN_PINDAH_RENDER.md)** — Render + MongoDB Atlas + cron-job.org, langkah lengkap.

> Alternatif tanpa proxy (isi `REACT_APP_BACKEND_URL` = URL backend) tetap bisa untuk API,
> tetapi foto anggota & sampul buku dimuat lewat path relatif `/api/...` sehingga **tidak tampil**.
> Gunakan mode proxy.

---

## 2. Environment variable

### Backend (`backend/.env`, contoh lengkap: `backend/.env.example`)
| Variabel | Wajib | Keterangan |
|---|---|---|
| `MONGO_URL` | Ã¢Å“â€¦ | String koneksi MongoDB (`mongodb+srv://...` dari Atlas). |
| `DB_NAME` | Ã¢Å“â€¦ | Nama database, mis. `perpus`. |
| `JWT_SECRET` | Ã¢Å“â€¦ | Ã¢â€°Â¥ 32 karakter acak. `python -c "import secrets;print(secrets.token_hex(32))"` |
| `FRONTEND_URL` | disarankan | URL frontend (tanpa `/` di akhir). Otomatis diizinkan CORS. |
| `CORS_ORIGINS` | opsional | Asal tambahan, dipisah koma. `*` = semua asal (hanya uji coba). |
| `CORS_ORIGIN_REGEX` | opsional | Regex asal yang diizinkan, mis. `^https://perpus-[a-z0-9-]+\.vercel\.app$` |

Aturan CORS (`backend/server.py`): asal yang diizinkan = `FRONTEND_URL` + `CORS_ORIGINS` + `CORS_ORIGIN_REGEX`.
Jika salah satu berisi `*`, semua asal diizinkan. Dengan mode proxy, CORS sebenarnya tidak dipakai.

### Frontend (`frontend/.env`, contoh: `frontend/.env.example`)
| Variabel | Keterangan |
|---|---|
| `REACT_APP_BACKEND_URL` | **Kosongkan** untuk mode proxy (disarankan). Isi URL backend tanpa `/api` hanya untuk dev lokal (`http://localhost:8001`). Ditanam saat build Ã¢â€ â€™ ubah = build ulang. |

### Vercel (Project Ã¢â€ â€™ Settings Ã¢â€ â€™ Environment Variables)
| Variabel | Keterangan |
|---|---|
| `BACKEND_URL` | URL backend tanpa `/api`, mis. `https://perpus-backend.onrender.com`. Dibaca `middleware.js`. |
| `REACT_APP_BACKEND_URL` | Biarkan kosong / jangan dibuat. |

---

## 3. Setup MongoDB Atlas (gratis)
1. Daftar di https://www.mongodb.com/cloud/atlas/register.
2. **Create cluster Ã¢â€ â€™ M0 Free**, provider AWS, region **Singapore (ap-southeast-1)**.
3. **Database Access Ã¢â€ â€™ Add New Database User**: username mis. `perpus`, password *Autogenerate* Ã¢â€ â€™ simpan.
   Hindari karakter `@ : / ? #` di password (atau URL-encode).
4. **Network Access Ã¢â€ â€™ Add IP Address Ã¢â€ â€™ Allow access from anywhere** (`0.0.0.0/0`) Ã¢â‚¬â€ IP Render/Vercel berubah-ubah.
5. **Database Ã¢â€ â€™ Connect Ã¢â€ â€™ Drivers Ã¢â€ â€™ Python** Ã¢â€ â€™ salin:
   `mongodb+srv://perpus:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   Ganti `<password>`. Ini nilai **`MONGO_URL`**. `DB_NAME` bebas (mis. `perpus`); database dibuat otomatis.
6. Saat backend pertama kali jalan dengan database kosong, akun contoh & data contoh dibuat otomatis
   dan indeks dibuat sendiri. Tidak perlu impor manual.

---

## 4. Deploy backend di Render (wajib untuk kedua opsi frontend)

**Cara Blueprint (otomatis):**
1. Push repo ke GitHub. Di https://render.com Ã¢â€ â€™ **New + Ã¢â€ â€™ Blueprint** Ã¢â€ â€™ pilih repo. Render membaca `render.yaml`
   (berisi `perpus-backend` + `perpus-frontend`). Jika frontend di Vercel, hapus layanan `perpus-frontend`
   dari `render.yaml` sebelum Apply, atau abaikan/suspend setelahnya.
2. Isi `MONGO_URL` (dari Atlas) dan `FRONTEND_URL` (URL frontend; bisa diisi setelah frontend jadi).
   `JWT_SECRET` dibuat otomatis oleh Render.
3. **Apply** Ã¢â€ â€™ tunggu status **Live**. Tes `https://<nama-backend>.onrender.com/api/` Ã¢â€ â€™
   `{"message":"Perpustakaan SMA Negeri 1 Abung Tengah aktif"}`.

**Cara manual (New + Ã¢â€ â€™ Web Service):**
| Isian | Nilai |
|---|---|
| Root Directory | `backend` |
| Runtime | Python 3 (env `PYTHON_VERSION=3.11.9`) |
| Build Command | `pip install -r requirements.prod.txt` |
| Start Command | `uvicorn server:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/` |
| Environment | `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `FRONTEND_URL` (lihat tabel di atas) |

`requirements.prod.txt` = paket yang benar-benar dipakai server (lebih cepat dibangun).
`requirements.txt` adalah daftar lengkap lingkungan pengembangan.

Catatan paket gratis Render: layanan tidur setelah Ã‚Â±15 menit tanpa akses; permintaan pertama Ã‚Â±50 detik.

---

## 5a. Deploy frontend di Vercel
1. https://vercel.com Ã¢â€ â€™ **Add New Ã¢â€ â€™ Project** Ã¢â€ â€™ import repo. **Root Directory: biarkan root repo** (`./`),
   karena `vercel.json` dan `middleware.js` ada di root.
2. Framework Preset: **Other** (konfigurasi diambil dari `vercel.json`:
   install `cd frontend && yarn install`, build `cd frontend && CI=false yarn build`, output `frontend/build`).
3. Environment Variables: **`BACKEND_URL`** = URL backend Render (tanpa `/api`). Jangan isi `REACT_APP_BACKEND_URL`.
4. Deploy. Buka `https://<proyek>.vercel.app/api/` Ã¢â€ â€™ harus menampilkan pesan backend aktif (lewat proxy).
5. Isi `FRONTEND_URL` di backend Render dengan URL Vercel, lalu redeploy backend.
6. Node: `package.json` meminta Node 22.x (Vercel Ã¢â€ â€™ Settings Ã¢â€ â€™ Node.js Version: 22.x).

## 5b. Deploy frontend di Render (Static Site)
1. Lewat Blueprint, layanan `perpus-frontend` dibuat otomatis dari `render.yaml`:
   root `frontend`, build `yarn install && CI=false yarn build`, publish `build`, `NODE_VERSION=22`.
2. **Penting:** rewrite `/api/*` di `render.yaml` menunjuk ke `https://perpus-backend.onrender.com/api/*`.
   Jika URL backend Anda berbeda (nama layanan sudah terpakai), ubah di `render.yaml`
   atau di Dashboard Ã¢â€ â€™ perpus-frontend Ã¢â€ â€™ **Redirects/Rewrites**. Urutan aturan: `/api/*` dulu, lalu `/*` Ã¢â€ â€™ `/index.html`.
3. Isi `FRONTEND_URL` backend dengan URL static site ini.

---

## 6. Cek setelah deploy
- [ ] `/<frontend>/api/` menampilkan pesan backend aktif.
- [ ] Login `/admin` dan `/siswa` berhasil.
- [ ] Tambah anggota + unggah foto Ã¢â€ â€™ foto tampil di kartu; tambah buku + sampul Ã¢â€ â€™ sampul tampil.
- [ ] **Scan QR** (Sirkulasi / Pengunjung) Ã¢â‚¬â€ butuh HTTPS + izin kamera (Vercel/Render sudah HTTPS).
- [ ] **Cetak kartu** (satu & massal, depan/belakang) dan **Cetak QR massal** buku.
- [ ] **Ekspor PDF/Excel** di Laporan, **Unduh cadangan**.
- [ ] **Reservasi buku** dari portal siswa Ã¢â€ â€™ muncul di antrean petugas.
- [ ] Ganti sandi akun bawaan (lihat di bawah) lewat menu **Akun & sandi**.

## 7. Akun bawaan & keamanan
Saat database kosong dibuat: `admin@smansa.sch.id / admin123`, `petugas@smansa.sch.id / petugas123`,
`siswa@smansa.sch.id / siswa123`. **Segera ganti sandinya di produksi.** Jangan pernah commit file `.env`.

## 8. Memindahkan data
Web lama: **Akun & sandi Ã¢â€ â€™ Unduh cadangan**. Web baru (login admin): **Akun & sandi Ã¢â€ â€™ Pulihkan data**.
Catatan: foto anggota (koleksi `files`) belum ikut dalam file cadangan.

## 9. Menjalankan lokal
```bash
# MongoDB lokal di mongodb://localhost:27017
cd backend && cp .env.example .env && pip install -r requirements.prod.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

cd frontend && cp .env.example .env   # isi REACT_APP_BACKEND_URL=http://localhost:8001
yarn install && yarn start
```
Catatan lokal: cookie login memakai `Secure`, jadi di `http://localhost` login berjalan lewat token Bearer
(sudah otomatis disimpan aplikasi).

## 10. Struktur
```
backend/      server.py + modul (visits, summary, loan_rank, reports_pdf, restore_big, purge, media), assets/, .env.example
frontend/     src/ (App.js, components/, *.css), public/ (PWA, logo), package.json, yarn.lock, .env.example
middleware.js Proxy /api untuk Vercel (env BACKEND_URL)
vercel.json   Build & header Vercel
render.yaml   Blueprint Render (backend + static site)
memory/       PRD.md (riwayat fitur)
```
