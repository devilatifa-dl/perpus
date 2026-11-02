# Panduan Deploy: MongoDB Atlas + Render + Vercel (gratis)

Urutannya: **1) Database (Atlas) → 2) Backend (Render) → 3) Sambungkan ke Vercel**.
Semua memakai paket gratis. Foto anggota dan seluruh data tersimpan di database Atlas.

## 1. Database: MongoDB Atlas
1. Buka https://www.mongodb.com/cloud/atlas/register, daftar (boleh dengan akun Google).
2. Buat cluster: pilih **M0 (Free)**, provider AWS, region **Singapore**, lalu **Create**.
3. Di jendela "Connect to Cluster" / menu **Database Access**: buat pengguna database
   - Username: `perpus`
   - Password: klik *Autogenerate*, lalu **salin dan simpan** (jangan memakai karakter `@` `:` `/`).
4. Menu **Network Access → Add IP Address → Allow access from anywhere** (`0.0.0.0/0`) → Confirm.
   (Diperlukan karena alamat IP Render berubah-ubah.)
5. Menu **Database → Connect → Drivers** → salin alamat seperti:
   `mongodb+srv://perpus:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   Ganti `<password>` dengan password tadi. Ini nilai **MONGO_URL** Anda.

## 2. Backend: Render
1. Buka https://render.com, daftar dengan akun GitHub `devilatifa-dl`.
2. **New + → Blueprint** → pilih repo `devilatifa-dl/perpus` → Render membaca file `render.yaml`.
3. Saat diminta mengisi variabel, isi **MONGO_URL** dengan alamat dari langkah 1.5. Lainnya sudah terisi otomatis.
4. Klik **Apply** dan tunggu build selesai (sekitar 5-10 menit). Status berubah menjadi **Live**.
5. Salin alamat layanan di bagian atas, bentuknya `https://perpus-backend-xxxx.onrender.com`.
6. Tes: buka `https://perpus-backend-xxxx.onrender.com/api/` di browser. Harus muncul
   `{"message":"Perpustakaan SMA Negeri 1 Abung Tengah aktif"}`.

Catatan paket gratis Render: layanan "tidur" setelah 15 menit tidak dipakai, sehingga
permintaan pertama bisa memakan waktu sekitar 50 detik. Setelah itu normal kembali.

## 3. Sambungkan ke Vercel
Di file `vercel.json`, ganti alamat tujuan `/api` dengan alamat Render dari langkah 2.5:

```json
{ "source": "/api/:path*", "destination": "https://perpus-backend-xxxx.onrender.com/api/:path*" }
```

Commit dan push perubahan itu. Vercel akan membangun ulang otomatis.

## 4. Akun awal dan keamanan
Saat database masih kosong, akun contoh dibuat otomatis (admin: `admin@smansa.sch.id`).
**Segera ganti password semua akun** lewat menu **Akun**, karena password awal ada di kode
dan siapa pun yang tahu alamat web bisa mencobanya.

## 5. Memindahkan data lama (opsional)
Di web lama: **Akun → Unduh cadangan (ZIP)**. Di web baru, login sebagai admin lalu
**Akun → Pulihkan data** dan pilih file ZIP itu. Foto anggota lama tidak ikut pindah.
