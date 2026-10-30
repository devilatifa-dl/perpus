"""Pulihkan data dari cadangan berukuran berapa pun.

Alur (dipakai menu Akun -> Pulihkan data):
  1. POST /admin/restore/start   {code, filename, size, chunks}  -> verifikasi kode email, buat sesi unggah
  2. PUT  /admin/restore/chunk?upload_id=..&index=..  (body = potongan berkas, maks CHUNK_SIZE)
  3. POST /admin/restore/finish  {upload_id}  -> proses di latar belakang
  4. GET  /admin/restore/status/{upload_id}  -> pantau kemajuan / hasil

Berkas dipotong kecil-kecil di browser sehingga tidak terkena batas ukuran unggahan server hosting.
Potongan disimpan di MongoDB (aman bila server punya lebih dari satu instance), lalu dibaca secara streaming
(ijson) dan dimasukkan ke koleksi sementara. Data lama baru diganti setelah SELURUH isi cadangan berhasil dibaca,
sehingga cadangan yang rusak tidak menghapus data yang ada.
"""
import asyncio, io, logging, os, tempfile, uuid, zipfile
from datetime import datetime, timedelta, timezone
from typing import Optional

import ijson
from bson.binary import Binary
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

logger = logging.getLogger("restore")
CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB per potongan (jauh di bawah batas hosting & batas dokumen MongoDB 16 MB)
BATCH = 500
JSON_MEMBER = "data-cadangan.json"


class StartInput(BaseModel):
    code: str
    filename: str = ""
    size: int = 0
    chunks: int


class FinishInput(BaseModel):
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


def _open_json(path):
    """Buka isi JSON dari berkas cadangan (.zip dari 'Unduh cadangan' atau .json lama). Lewati BOM UTF-8."""
    with open(path, "rb") as fh:
        is_zip = fh.read(2) == b"PK"
    if is_zip:
        try:
            z = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            raise RestoreError("Berkas ZIP cadangan rusak")
        if JSON_MEMBER not in z.namelist():
            z.close()
            raise RestoreError(f"ZIP cadangan tidak berisi {JSON_MEMBER}")
        f = z.open(JSON_MEMBER)
        f._zip_parent = z  # tutup ZIP bersama berkasnya
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
            raise RestoreError("Berkas cadangan tidak valid (bukan JSON atau terpotong)")
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
            await set_job(upload_id, status="done", restored=restored, finished_at=_now())
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

    @r.post("/admin/restore/start")
    async def start(data: StartInput, user=Depends(current_user)):
        admin_only(user)
        if data.chunks < 1:
            raise HTTPException(400, "Berkas cadangan kosong")
        if await db.restore_uploads.find_one({"status": "processing"}, {"_id": 0, "id": 1}):
            raise HTTPException(409, "Pemulihan lain sedang berjalan. Tunggu sampai selesai.")
        await verify_reset_code(data.code, "restore")
        # Bersihkan sisa sesi lama yang tidak selesai
        old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        for j in await db.restore_uploads.find({"created_at": {"$lt": old}}, {"_id": 0, "id": 1}).to_list(1000):
            await db.restore_chunks.delete_many({"upload_id": j["id"]})
        await db.restore_uploads.delete_many({"created_at": {"$lt": old}})
        upload_id = "RS-" + uuid.uuid4().hex[:12].upper()
        await db.restore_uploads.insert_one({"id": upload_id, "user_id": user["id"], "filename": data.filename[:200], "size": max(0, data.size),
                                             "chunks": data.chunks, "status": "uploading", "created_at": _now(), "updated_at": _now()})
        await db.restore_chunks.create_index([("upload_id", 1), ("idx", 1)])
        return {"upload_id": upload_id, "chunk_size": CHUNK_SIZE}

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
        return {k: job.get(k) for k in ("id", "status", "progress", "restored", "error", "filename", "size")}

    # Unggahan sekali kirim (kompatibel dengan versi lama) — tanpa batas ukuran dari aplikasi.
    @r.post("/admin/restore")
    async def restore_once(file: UploadFile = File(...), code: str = Form(""), user=Depends(current_user)):
        admin_only(user)
        await verify_reset_code(code, "restore")
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
            return {"ok": True, "restored": restored}
        finally:
            if os.path.exists(path):
                os.remove(path)

    return r
