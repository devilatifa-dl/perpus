# Panduan Pindah dari Emergent ke Render + Atlas (100% Gratis)

Panduan ini memindahkan backend dari Emergent ke **Render** dan database ke **MongoDB Atlas**,
tanpa biaya dan tanpa langganan. Frontend tetap di **Vercel**.

```
Browser --> Vercel (frontend React)  --/api/*-->  Render (FastAPI)  -->  MongoDB Atlas
```

**Total biaya: Rp 0.** Tidak ada kartu kredit yang diperlukan.

---

## Urutan aman (tanpa downtime)

Situs **tetap hidup** selama proses pindah. Backend cadangan di `vercel.json` dipakai sampai
Anda mengisi `BACKEND_URL` di Vercel.

| Urutan | Langkah | Situs |
|---|---|---|
| 1 | Buat MongoDB Atlas | jalan (backend cadangan) |
| 2 | Deploy backend Render, tunggu **Live** | jalan (backend cadangan) |
| 3 | Uji `https://<backend-render>/api/` harus balas `{"message":"...aktif"}` | jalan |
| 4 | Isi `BACKEND_URL` di Vercel lalu **Redeploy** | sekitar 1 menit saat redeploy |
| 5 | Pulihkan data | jalan (backend Render) |
| 6 | Daftar cron-job.org | jalan |

**Jangan lakukan langkah 4 sebelum langkah 3 lulus.** Kalau backend Render belum Live,
situs akan error karena `/api/` tidak punya tujuan.

---

## Ringkasan yang harus dilakukan

| # | Langkah | Perkiraan waktu |
|---|---|---|
| 1 | Buat cluster MongoDB Atlas M0 (gratis) | 10 menit |
| 2 | Deploy backend ke Render via Blueprint | 10 menit |
| 3 | Set `BACKEND_URL` di Vercel | 2 menit |
| 4 | Pulihkan data dari cadangan | 5 menit |
| 5 | Daftar cron-job.org agar backend tidak tidur | 5 menit |
| 6 | Verifikasi | 5 menit |

---

## 1. MongoDB Atlas (gratis permanen, 512 MB)

1. Buka https://www.mongodb.com/cloud/atlas/register lalu daftar (bisa pakai Google).
2. **Create** lalu pilih **M0 FREE**.
   - Provider: **AWS**
   - Region: **Singapore (ap-southeast-1)**, paling dekat ke Indonesia
   - Name: `perpus`
3. **Create Deployment**, tunggu sekitar 3 menit sampai cluster siap.
4. **Security > Database Access > Add New Database User**
   - Authentication: **Password**
   - Username: `perpus`
   - Password: klik **Autogenerate Secure Password**, lalu **SALIN dan SIMPAN**
   - Database User Privileges: **Read and write to any database**
   - **Add User**
5. **Security > Network Access > Add IP Address**
   - Pilih **Allow Access from Anywhere** (`0.0.0.0/0`)
   - **Confirm**
   - Wajib, karena IP Render berubah-ubah.
6. **Database > Connect > Drivers**
   - Driver: **Python**, Version: **3.11 or later**
   - Salin connection string, bentuknya:

     ```
     mongodb+srv://perpus:<password>@perpus.xxxxx.mongodb.net/?retryWrites=true&w=majority
     ```

   - **Ganti `<password>`** dengan password dari langkah 4.
   - Tambahkan nama database sebelum tanda `?`:

     ```
     mongodb+srv://perpus:PASSWORD@perpus.xxxxx.mongodb.net/perpus?retryWrites=true&w=majority
     ```

> **Simpan string ini.** Akan dipakai di langkah 2.

---

## 2. Deploy backend ke Render

1. Buka https://render.com, **Get Started**, daftar dengan **GitHub**.
2. **New +** lalu **Blueprint**.
3. Pilih repo **`devilatifa-dl/perpus`**, klik **Connect**.
4. Render membaca `render.yaml` dan menampilkan layanan **`perpus-backend`**.
5. Isi environment variable yang diminta:

   | Key | Nilai |
   |---|---|
   | `MONGO_URL` | connection string dari langkah 1 |
   | `FRONTEND_URL` | `https://perpusmansa.vercel.app` |

   `JWT_SECRET` dibuat otomatis oleh Render. `DB_NAME` sudah `perpus`.

6. **Apply**, tunggu status **Live** (sekitar 5 menit untuk build pertama).
7. Catat URL backend Anda, bentuknya:

   ```
   https://perpus-backend.onrender.com
   ```

> **Kalau nama `perpus-backend` sudah dipakai** (misalnya dari percobaan sebelumnya), Render akan
> memberi nama lain seperti `perpus-backend-abc1`. Pakai URL yang Anda dapat di langkah 3.

### Uji backend

Buka di browser:

```
https://perpus-backend.onrender.com/api/
```

Harus muncul:

```json
{"message":"Perpustakaan SMA Negeri 1 Abung Tengah aktif"}
```

> Permintaan pertama setelah lama tidak diakses bisa sekitar 50 detik (layanan bangun dari tidur).

---

## 3. Arahkan Vercel ke backend Render

1. Buka https://vercel.com, pilih project **perpusmansa**, lalu **Settings > Environment Variables**.
2. **Add New**:

   | Key | Value | Environment |
   |---|---|---|
   | `BACKEND_URL` | `https://perpus-backend.onrender.com` | Production, Preview, Development |

3. **Save**.
4. **Deployments**, pilih deployment terakhir, klik **...**, lalu **Redeploy** (agar env terbaca).

> **Ini satu-satunya langkah yang perlu Anda lakukan di Vercel.** Tidak perlu mengubah kode
> atau push ulang: `middleware.js` membaca `BACKEND_URL` dan meneruskan `/api/*` ke sana,
> menimpa tujuan bawaan di `vercel.json`.
>
> Selama env kosong, situs tetap hidup memakai backend cadangan di `vercel.json`,
> jadi tidak ada downtime saat berpindah.

### Uji

Buka https://perpusmansa.vercel.app/api/ dan pastikan muncul pesan yang sama seperti langkah 2.

---

## 4. Pulihkan data

Database Atlas masih kosong. Aplikasi akan membuat data contoh otomatis saat pertama diakses.

1. Buka https://perpusmansa.vercel.app/admin
2. Login: `admin@smansa.sch.id` / `admin123`
3. **Akun & sandi** lalu **Pulihkan data**
4. Pilih `backup-perpustakaan-2026-11-06.zip` (atau cadangan terbaru Anda)
5. Tunggu sampai selesai, halaman akan reload otomatis

Setelah selesai: **412 anggota, 101 buku, 108 transaksi, 116 kunjungan**.

> **Penting:** segera ganti kata sandi admin bawaan setelah pemulihan
> (menu **Akun & sandi > Ubah kata sandi saya**).

---

## 5. Cron-job.org - agar backend tidak tidur

Render paket gratis tidur setelah sekitar 15 menit tanpa akses. Cron-job.org memanggil backend
secara berkala sehingga tetap bangun.

1. Buka https://cron-job.org, **Sign up** (gratis, cukup email).
2. **Cronjobs** lalu **Create cronjob**.
3. Isi:

   | Field | Nilai |
   |---|---|
   | **Title** | `Perpus Backend Keep-Alive` |
   | **URL** | `https://perpus-backend.onrender.com/api/` |
   | **Schedule** | Every **10 minutes** |
   | **Request method** | `GET` |
   | **Enable job** | dicentang |

4. **Advanced** (opsional tapi disarankan):
   - **Timeout**: `60` detik (agar tidak gagal saat backend bangun)
   - **Save responses in job history**: aktifkan (untuk memantau)
5. **Create**.

### Batas paket gratis cron-job.org

| Batas | Nilai |
|---|---|
| Jumlah job | 50 |
| Interval minimum | 1 menit |
| Waktu eksekusi maksimum | 30 detik (bisa dinaikkan di Advanced) |

Satu job dengan interval 10 menit jauh di bawah semua batas.

> **Catatan:** Render memberi 750 jam layanan gratis per bulan. Satu layanan yang selalu
> bangun sekitar 730 jam/bulan, masih di bawah batas. Kalau Anda juga membuat layanan lain,
> kurangi frekuensi cron atau matikan layanan yang tidak dipakai.

---

## 6. Verifikasi

Jalankan berurutan:

| # | Uji | Harapan |
|---|---|---|
| 1 | `https://perpus-backend.onrender.com/api/` | `{"message":"...aktif"}` |
| 2 | `https://perpusmansa.vercel.app/api/` | pesan sama (bukti proxy jalan) |
| 3 | Login admin di `/admin` | masuk dashboard |
| 4 | Menu **Anggota** | 412 anggota, grup "Guru" di atas |
| 5 | Menu **Laporan > Peringkat rajin berkunjung** | tab Siswa dan Guru terpisah |
| 6 | Menu **Pengunjung** | indikator **Online** |
| 7 | **Akun & sandi > Unduh cadangan** | ZIP terunduh |
| 8 | **Akun & sandi > Pulihkan data** | berhasil tanpa error 413 |
| 9 | Foto anggota (menu Anggota, kelas X.4) | foto tampil |

---

## Setelah pindah: matikan Emergent

Setelah semua uji di atas lulus, backend Emergent tidak dipakai lagi. Tidak ada tindakan
khusus yang diperlukan, cukup berhenti berlangganan atau biarkan kedaluwarsa.

Untuk memastikan tidak ada sisa ketergantungan, cek:

```powershell
Select-String -Path vercel.json,middleware.js -Pattern 'emergent'
```

Harus **tidak ada hasil**.

---

## Pemeliharaan rutin

| Kapan | Apa |
|---|---|
| Setiap minggu | **Akun & sandi > Unduh cadangan** (simpan di 2 tempat) |
| Setiap bulan | Cek dashboard Render: pemakaian jam dan error log |
| Setiap bulan | Cek dashboard Atlas: pemakaian storage (batas 512 MB) |
| Setelah tambah fitur | Push ke GitHub, Render dan Vercel auto-deploy |

---

## Kalau ada masalah

| Gejala | Penyebab | Solusi |
|---|---|---|
| `/api/` di Vercel 404 | `BACKEND_URL` belum diisi atau belum redeploy | Isi env lalu **Redeploy** |
| `/api/` di Vercel 502 | Backend Render sedang bangun | Tunggu 60 detik, ulangi |
| Login gagal, data kosong | `MONGO_URL` salah | Cek password dan nama database di string |
| `ServerSelectionTimeoutError` | IP Atlas belum diizinkan | Network Access, isi `0.0.0.0/0` |
| Foto 404 | Foto tidak ada di cadangan | Unggah ulang lewat **Anggota > Edit > Foto** |
| Backend lambat setiap pagi | Layanan tidur | Pastikan cron-job.org aktif |
| Build Render gagal | `requirements.prod.txt` bermasalah | Cek log Render, tab **Logs** |

---

## Alternatif kalau Render terasa lambat

| Opsi | Biaya | Kelebihan | Kekurangan |
|---|---|---|---|
| **Render free** (panduan ini) | Rp 0 | Tanpa kartu kredit | Tidur 15 menit |
| **Fly.io** | Rp 0 (kredit terbatas) | Tidak tidur | Perlu kartu kredit |
| **VPS** IDCloudHost/Contabo | sekitar Rp 30-50rb/bulan | Selalu cepat, kontrol penuh | Berbayar |
| **Server sekolah** | Rp 0 | Data di lokasi sendiri | Butuh PC selalu nyala dan IP publik |

Untuk perpustakaan sekolah dengan pemakaian jam belajar, **Render free + cron-job.org**
sudah lebih dari cukup.
