"""Entry point backend FastAPI untuk Vercel (Python serverless).

Vercel mencari file di folder `api/` dan menjalankan variabel `app` sebagai
handler ASGI. Modul backend asli ada di `backend/`, jadi kita tambahkan ke
sys.path lalu impor `server:app` apa adanya tanpa mengubah kode backend.

Catatan penting:
- Setiap request bisa masuk ke instance berbeda, jadi koneksi MongoDB harus
  dibuat ulang per instance (motor sudah menangani connection pool sendiri).
- Batas body request Vercel 4.5 MB. Unggah foto (maks 25 MB) dan pulihkan
  cadangan (potongan 3 MB) sudah disesuaikan di sisi frontend.
"""

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
BACKEND = AKAR / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Vercel tidak menyediakan .env; semua lewat Environment Variables.
os.environ.setdefault("DB_NAME", "perpus")

from server import app  # noqa: E402  (harus setelah sys.path diatur)

__all__ = ["app"]
