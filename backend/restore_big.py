"""Pulihkan data dari cadangan berukuran berapa pun.

Alur utama (dipakai menu Akun -> Pulihkan data):
  1. POST /admin/restore/begin   {filename, size, collections}  -> buat sesi (admin, tanpa kode email)
  2. POST /admin/restore/batch?upload_id=..&collection=..  (body = potongan JSON berisi daftar entri)
  3. POST /admin/restore/commit  {upload_id}  -> tukar koleksi sementara menjadi data aktif
  4. POST /admin/restore/abort   {upload_id}  -> batalkan & bersihkan

Browser membaca isi cadangan lalu mengirimnya per potongan kecil (di bawah batas body request hosting),
sehingga setiap permintaan selesai jauh di bawah batas waktu hosting serverless (Vercel 60 detik) dan
tidak ada berkas besar yang perlu dibaca ulang dari database. Data lama baru diganti pada langkah commit,
jadi cadangan yang rusak tidak menghapus data yang ada.

Alur lama (start/chunk/finish/status) tetap tersedia untuk kompatibilitas dan pemakaian di server biasa.
"""
import asyncio, io, logging, mmap, os, struct, tempfile, uuid, zipfile, zlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import ijson
from bson.binary import Binary
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

logger = logging.getLogger("restore")
# Vercel menolak body request > 4,5 MB (FUNCTION_PAYLOAD_TOO_LARGE) sebelum sampai ke backend.
# Potongan dibuat 3 MB agar aman di semua hosting; jumlah potongan menyesuaikan ukuran berkas,
# sehingga cadangan berukuran berapa pun (100 MB, 1 GB, ...) tetap bisa dipulihkan.
CHUNK_SIZE = 3 * 1024 * 1024
MAX_RESTORE = 2 * 1024 * 1024 * 1024  # batas wajar ukuran berkas cadangan (2 GB)
BATCH = 500
# Batas ukuran satu potongan data pada alur bertahap (begin/batch/commit). Dijaga di bawah 4,5 MB
# (batas body request Vercel) dan cukup kecil agar satu permintaan selesai dalam hitungan detik.
STEP_BYTES = 2 * 1024 * 1024
JSON_MEMBER = "data-cadangan.json"


class StartInput(BaseModel):
    code: str = ""
    filename: str = ""
    size: int = 0
    chunks: int = 0  # opsional: server menghitung sendiri dari `size`


class FinishInput(BaseModel):
    upload_id: str


class BeginInput(BaseModel):
    filename: str = ""
    size: int = 0
    collections: list[str] = []


class BatchInput(BaseModel):
    upload_id: str
    collection: str
    items: list[dict] = []
    last: bool = False


class UploadIdInput(BaseModel):
    upload_id: str


class RestoreError(Exception):
    pass


class _AsyncReader:
    """Pembungkus berkas biasa agar ijson membaca secara async (event loop tidak tertahan)."""
    def __init__(self, f):
        self.f = f

    async def read(self, n=-1):
        return await asyncio.to_thread(self.f.read, n)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _is_json_member(name):
    return name == JSON_MEMBER or name.endswith("/" + JSON_MEMBER)


class _LocalMemberReader(io.RawIOBase):
    """Baca satu berkas di dalam ZIP langsung dari 'local file header'.
    Dipakai bila ZIP terpotong (daftar isi di akhir berkas hilang) — data-cadangan.json selalu ditulis
    paling awal sehingga biasanya masih utuh dan bisa diselamatkan."""

    def __init__(self, fh, method, csize):
        super().__init__()
        self.fh, self.method = fh, method
        self.left = csize if csize else None
        self.d = zlib.decompressobj(-15) if method == 8 else None
        self.buf, self.eof = b"", False

    def readable(self):
        return True

    def readinto(self, b):
        while not self.buf and not self.eof:
            n = 1 << 20 if self.left is None else min(1 << 20, self.left)
            raw = self.fh.read(n) if n > 0 else b""
            if self.left is not None:
                self.left -= len(raw)
            if not raw:
                if self.d:
                    self.buf += self.d.flush()
                self.eof = True
                break
            if self.d:
                self.buf += self.d.decompress(raw)
                if self.d.eof:
                    self.eof = True
            else:
                self.buf += raw
        n = min(len(b), len(self.buf))
        b[:n] = self.buf[:n]
        self.buf = self.buf[n:]
        return n

    def close(self):
        try:
            self.fh.close()
        finally:
            super().close()


def _open_from_local_header(path):
    """Cari data-cadangan.json lewat tanda 'PK\\x03\\x04' (tanpa daftar isi ZIP)."""
    with open(path, "rb") as fh:
        with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            pos = mm.find(b"PK\x03\x04")
            while pos != -1 and pos + 30 <= len(mm):
                (_sig, _ver, flag, method, _t, _d, _crc, csize, _usize, nlen, elen) = struct.unpack("<4sHHHHHIIIHH", mm[pos:pos + 30])
                name = mm[pos + 30:pos + 30 + nlen].decode("utf-8", "replace")
                if _is_json_member(name) and method in (0, 8):
                    start = pos + 30 + nlen + elen
                    if flag & 0x08 or csize == 0xFFFFFFFF:
                        csize = 0  # ukuran tidak tercatat di header -> baca sampai aliran deflate selesai
                    f = open(path, "rb")
                    f.seek(start)
                    return io.BufferedReader(_LocalMemberReader(f, method, csize), buffer_size=1024 * 1024)
                pos = mm.find(b"PK\x03\x04", pos + 4)
    return None


def _zip_damaged(path):
    """True bila berkas berupa ZIP tetapi daftar isinya rusak/terpotong."""
    try:
        with open(path, "rb") as fh:
            if fh.read(2) != b"PK":
                return False
        zipfile.ZipFile(path).close()
        return False
    except zipfile.BadZipFile:
        return True
    except Exception:
        return False


def _open_json(path):
    """Buka isi JSON dari berkas cadangan (.zip dari 'Unduh cadangan' atau .json lama). Lewati BOM UTF-8.
    ZIP yang terpotong (unduhan tidak selesai) tetap dicoba diselamatkan."""
    with open(path, "rb") as fh:
        is_zip = fh.read(2) == b"PK"
    if is_zip:
        f = None
        try:
            z = zipfile.ZipFile(path)
            member = next((n for n in z.namelist() if _is_json_member(n)), None)
            if not member:
                z.close()
                raise RestoreError(f"ZIP cadangan tidak berisi {JSON_MEMBER}")
            f = z.open(member)
            f._zip_parent = z  # tutup ZIP bersama berkasnya
        except zipfile.BadZipFile:
            f = _open_from_local_header(path)
            if f is None:
                raise RestoreError("Berkas ZIP cadangan rusak/terpotong dan data-cadangan.json tidak ditemukan. Unduh ulang cadangan lalu coba lagi.")
            logger.warning("ZIP cadangan tidak utuh, memakai pemulihan dari local header: %s", path)
    else:
        f = open(path, "rb")
    buf = io.BufferedReader(f, buffer_size=1024 * 1024) if not hasattr(f, "peek") else f
    if buf.peek(3)[:3] == b"\xef\xbb\xbf":
        buf.read(3)
    return buf


def _close(f):
    try:
        f.close()
        z = getattr(f, "_zip_parent", None) or getattr(getattr(f, "raw", None), "_zip_parent", None)
        if z:
            z.close()
    except Exception:
        pass


def build_router(db, current_user, verify_reset_code, normalize_books, collections):
    r = APIRouter()
    tasks = set()  # simpan referensi agar tugas latar belakang tidak dibersihkan sebelum selesai

    def admin_only(user):
        if user.get("role") != "admin":
            raise HTTPException(403, "Hanya admin yang dapat memulihkan data")

    async def set_job(upload_id, **fields):
        await db.restore_uploads.update_one({"id": upload_id}, {"$set": {**fields, "updated_at": _now()}})

    async def process_file(path, progress=None):
        """Baca cadangan secara streaming -> koleksi sementara -> ganti data lama. Mengembalikan jumlah per koleksi."""
        async def report(**kw):
            if progress:
                await progress(**kw)

        # 1) Validasi: JSON utuh & struktur dikenali (tanpa memuat isi ke memori)
        await report(stage="memeriksa", collection="", inserted=0)
        f = _open_json(path)
        kinds, has_collections = {}, False
        try:
            pending = None
            async for prefix, event, value in ijson.parse(_AsyncReader(f)):
                if prefix == "collections" and event == "start_map":
                    has_collections = True
                elif prefix == "collections" and event == "map_key":
                    pending = value
                elif pending is not None and prefix == f"collections.{pending}":
                    kinds[pending] = event
                    pending = None
        except ijson.JSONError:
            raise RestoreError("Isi data-cadangan.json tidak lengkap (berkas terpotong) atau bukan JSON. Unduh ulang cadangan lalu coba lagi.")
        except (zlib.error, zipfile.BadZipFile, EOFError):
            raise RestoreError("Berkas ZIP cadangan rusak/terpotong. Unduh ulang cadangan lalu coba lagi.")
        finally:
            _close(f)
        if not has_collections:
            raise RestoreError("Struktur berkas cadangan tidak dikenali")
        for name in collections:
            if name in kinds and kinds[name] not in ("start_array", "null"):
                raise RestoreError(f"Data '{name}' pada cadangan tidak valid")
        todo = [n for n in collections if kinds.get(n) == "start_array"]
        if not todo:
            raise RestoreError("Berkas cadangan tidak berisi data perpustakaan")

        # 2) Masukkan ke koleksi sementara
        staged = {}
        try:
            for name in todo:
                tmp = f"_restore_tmp_{name}"
                await db[tmp].drop()
                count, batch = 0, []
                f = _open_json(path)
                try:
                    async for item in ijson.items(_AsyncReader(f), f"collections.{name}.item", use_float=True):
                        if not isinstance(item, dict):
                            continue
                        item.pop("_id", None)
                        batch.append(item)
                        if len(batch) >= BATCH:
                            await db[tmp].insert_many(batch, ordered=False)
                            count += len(batch); batch = []
                            await report(stage="memuat", collection=name, inserted=count)
                    if batch:
                        await db[tmp].insert_many(batch, ordered=False)
                        count += len(batch)
                finally:
                    _close(f)
                staged[name] = count
                await report(stage="memuat", collection=name, inserted=count)

            # 3) Semua berhasil dibaca -> ganti data lama (indeks koleksi tetap dipertahankan oleh $out)
            await report(stage="mengganti", collection="", inserted=sum(staged.values()))
            for name, count in staged.items():
                if count:
                    await db[f"_restore_tmp_{name}"].aggregate([{"$match": {}}, {"$out": name}]).to_list(None)
                else:
                    await db[name].delete_many({})
        finally:
            for name in todo:
                await db[f"_restore_tmp_{name}"].drop()

        if await db.books.count_documents({"stock": {"$exists": False}}) > 0:
            await normalize_books()
        await db.meta.update_one({"id": "seed"}, {"$set": {"id": "seed", "done": True}}, upsert=True)
        return staged

    async def run_job(upload_id):
        path = None
        try:
            job = await db.restore_uploads.find_one({"id": upload_id}, {"_id": 0})
            fd, path = tempfile.mkstemp(prefix="perpus-restore-", suffix=".bin")
            with os.fdopen(fd, "wb") as out:
                for i in range(job["chunks"]):
                    ch = await db.restore_chunks.find_one({"upload_id": upload_id, "idx": i}, {"_id": 0, "data": 1})
                    if not ch:
                        raise RestoreError(f"Potongan berkas ke-{i + 1} hilang. Ulangi pemulihan.")
                    await asyncio.to_thread(out.write, ch["data"])
            await db.restore_chunks.delete_many({"upload_id": upload_id})

            async def progress(**kw):
                await set_job(upload_id, progress=kw)

            restored = await process_file(path, progress)
            await set_job(upload_id, status="done", restored=restored, salvaged=_zip_damaged(path), finished_at=_now())
        except RestoreError as e:
            await set_job(upload_id, status="error", error=str(e))
        except Exception as e:  # jangan biarkan sesi menggantung tanpa kabar
            logger.exception("restore failed")
            await set_job(upload_id, status="error", error=f"Pemulihan gagal: {e}")
        finally:
            await db.restore_chunks.delete_many({"upload_id": upload_id})
            if path and os.path.exists(path):
                os.remove(path)

    async def own_upload(upload_id, user, status=None):
        job = await db.restore_uploads.find_one({"id": upload_id}, {"_id": 0})
        if not job or job.get("user_id") != user["id"]:
            raise HTTPException(404, "Sesi pemulihan tidak ditemukan. Ulangi dari awal.")
        if status and job.get("status") != status:
            raise HTTPException(400, "Sesi pemulihan sudah tidak aktif. Ulangi dari awal.")
        return job

    # ------------------------------------------------------------------
    # Alur bertahap: browser mengirim isi cadangan per potongan kecil.
    # Setiap permintaan selesai dalam hitungan detik sehingga aman untuk
    # hosting serverless yang memutus proses setelah 60 detik.
    # ------------------------------------------------------------------
    def _tmp(name):
        return f"_restore_tmp_{name}"

    async def _drop_tmp(names):
        for name in names:
            try:
                await db[_tmp(name)].drop()
            except Exception:
                pass

    @r.post("/admin/restore/begin")
    async def begin(data: BeginInput, user=Depends(current_user)):
        admin_only(user)
        size = max(0, data.size)
        if size > MAX_RESTORE:
            raise HTTPException(400, f"Ukuran cadangan melebihi batas {MAX_RESTORE // (1024 * 1024)} MB")
        names = [n for n in data.collections if n in collections]
        if not names:
            raise HTTPException(400, "Berkas cadangan tidak berisi data perpustakaan")
        # Sesi lama yang menggantung tidak boleh menghalangi pemulihan baru.
        for j in await db.restore_uploads.find({"status": {"$in": ["uploading", "processing"]}}, {"_id": 0, "id": 1}).to_list(100):
            await _drop_tmp(collections)
            await db.restore_uploads.update_one({"id": j["id"]}, {"$set": {"status": "error", "error": "Dibatalkan karena ada pemulihan baru", "updated_at": _now()}})
        old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        await db.restore_uploads.delete_many({"created_at": {"$lt": old}})
        await _drop_tmp(collections)
        upload_id = "RS-" + uuid.uuid4().hex[:12].upper()
        await db.restore_uploads.insert_one({
            "id": upload_id, "user_id": user["id"], "filename": (data.filename or "")[:200], "size": size,
            "mode": "step", "status": "uploading", "collections": names, "counts": {},
            "created_at": _now(), "updated_at": _now(),
        })
        return {"upload_id": upload_id, "max_bytes": STEP_BYTES, "collections": names}

    @r.post("/admin/restore/batch")
    async def batch(data: BatchInput, user=Depends(current_user)):
        admin_only(user)
        job = await own_upload(data.upload_id, user, "uploading")
        name = data.collection
        if name not in job.get("collections", []):
            raise HTTPException(400, f"Koleksi '{name}' tidak ada pada berkas cadangan ini")
        docs = []
        for item in data.items:
            if isinstance(item, dict):
                item.pop("_id", None)
                docs.append(item)
        if docs:
            await db[_tmp(name)].insert_many(docs, ordered=False)
        counts = dict(job.get("counts") or {})
        counts[name] = counts.get(name, 0) + len(docs)
        await set_job(data.upload_id, counts=counts, progress={"stage": "memuat", "collection": name, "inserted": counts[name]})
        return {"ok": True, "collection": name, "inserted": counts[name]}

    @r.post("/admin/restore/commit")
    async def commit(data: UploadIdInput, user=Depends(current_user)):
        admin_only(user)
        job = await own_upload(data.upload_id, user, "uploading")
        names = job.get("collections", [])
        counts = job.get("counts") or {}
        await set_job(data.upload_id, status="processing", progress={"stage": "mengganti", "collection": "", "inserted": sum(counts.values())})
        restored = {}
        try:
            for name in names:
                count = counts.get(name, 0)
                if count:
                    await db[_tmp(name)].aggregate([{"$match": {}}, {"$out": name}]).to_list(None)
                else:
                    await db[name].delete_many({})
                restored[name] = count
            if await db.books.count_documents({"stock": {"$exists": False}}) > 0:
                await normalize_books()
            await db.meta.update_one({"id": "seed"}, {"$set": {"id": "seed", "done": True}}, upsert=True)
        except Exception as e:
            logger.exception("restore commit failed")
            await set_job(data.upload_id, status="error", error=f"Pemulihan gagal: {e}")
            raise HTTPException(500, f"Pemulihan gagal: {e}")
        finally:
            await _drop_tmp(names)
        await set_job(data.upload_id, status="done", restored=restored, finished_at=_now())
        return {"ok": True, "restored": restored}

    @r.post("/admin/restore/abort")
    async def abort(data: UploadIdInput, user=Depends(current_user)):
        admin_only(user)
        job = await own_upload(data.upload_id, user)
        await _drop_tmp(job.get("collections") or collections)
        await db.restore_uploads.update_one({"id": data.upload_id}, {"$set": {"status": "error", "error": "Dibatalkan oleh admin", "updated_at": _now()}})
        return {"ok": True}

    @r.post("/admin/restore/start")
    async def start(data: StartInput, user=Depends(current_user)):
        admin_only(user)
        size = max(0, data.size)
        if size > MAX_RESTORE:
            raise HTTPException(400, f"Ukuran cadangan melebihi batas {MAX_RESTORE // (1024 * 1024)} MB")
        # Jumlah potongan dihitung server dari ukuran berkas, jadi klien versi lama pun tetap cocok.
        chunks = max(1, -(-size // CHUNK_SIZE)) if size else max(1, data.chunks)
        if chunks < 1:
            raise HTTPException(400, "Berkas cadangan kosong")
        if await db.restore_uploads.find_one({"status": "processing"}, {"_id": 0, "id": 1}):
            raise HTTPException(409, "Pemulihan lain sedang berjalan. Tunggu sampai selesai.")
        # Tanpa kode email (keputusan pengguna): cukup admin + konfirmasi di aplikasi
        # Bersihkan sisa sesi lama yang tidak selesai
        old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        for j in await db.restore_uploads.find({"created_at": {"$lt": old}}, {"_id": 0, "id": 1}).to_list(1000):
            await db.restore_chunks.delete_many({"upload_id": j["id"]})
        await db.restore_uploads.delete_many({"created_at": {"$lt": old}})
        upload_id = "RS-" + uuid.uuid4().hex[:12].upper()
        await db.restore_uploads.insert_one({"id": upload_id, "user_id": user["id"], "filename": data.filename[:200], "size": size,
                                             "chunks": chunks, "status": "uploading", "created_at": _now(), "updated_at": _now()})
        await db.restore_chunks.create_index([("upload_id", 1), ("idx", 1)])
        return {"upload_id": upload_id, "chunk_size": CHUNK_SIZE, "chunks": chunks}

    @r.put("/admin/restore/chunk")
    async def chunk(request: Request, upload_id: str, index: int, user=Depends(current_user)):
        admin_only(user)
        job = await own_upload(upload_id, user, "uploading")
        if not 0 <= index < job["chunks"]:
            raise HTTPException(400, "Urutan potongan tidak valid")
        body = await request.body()
        if not body or len(body) > CHUNK_SIZE:
            raise HTTPException(400, "Ukuran potongan tidak valid")
        await db.restore_chunks.update_one({"upload_id": upload_id, "idx": index}, {"$set": {"upload_id": upload_id, "idx": index, "data": Binary(body)}}, upsert=True)
        return {"ok": True, "index": index}

    @r.post("/admin/restore/finish")
    async def finish(data: FinishInput, user=Depends(current_user)):
        admin_only(user)
        job = await own_upload(data.upload_id, user, "uploading")
        got = await db.restore_chunks.count_documents({"upload_id": data.upload_id})
        if got != job["chunks"]:
            raise HTTPException(400, f"Baru {got} dari {job['chunks']} potongan terunggah. Ulangi pemulihan.")
        await set_job(data.upload_id, status="processing", progress={"stage": "menyiapkan", "collection": "", "inserted": 0})
        t = asyncio.create_task(run_job(data.upload_id)); tasks.add(t); t.add_done_callback(tasks.discard)
        return {"ok": True}

    @r.get("/admin/restore/status/{upload_id}")
    async def status(upload_id: str, user=Depends(current_user)):
        admin_only(user)
        job = await own_upload(upload_id, user)
        return {k: job.get(k) for k in ("id", "status", "progress", "restored", "error", "filename", "size", "salvaged")}

    # Unggahan sekali kirim (kompatibel dengan versi lama) — tanpa batas ukuran dari aplikasi.
    @r.post("/admin/restore")
    async def restore_once(file: UploadFile = File(...), code: str = Form(""), user=Depends(current_user)):
        admin_only(user)
        fd, path = tempfile.mkstemp(prefix="perpus-restore-", suffix=".bin")
        try:
            with os.fdopen(fd, "wb") as out:
                while True:
                    part = await file.read(CHUNK_SIZE)
                    if not part:
                        break
                    await asyncio.to_thread(out.write, part)
            try:
                restored = await process_file(path)
            except RestoreError as e:
                raise HTTPException(400, str(e))
            return {"ok": True, "restored": restored, "salvaged": _zip_damaged(path)}
        finally:
            if os.path.exists(path):
                os.remove(path)

    return r
