import io, uuid, logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()
logger = logging.getLogger("media")

# Foto disimpan langsung di MongoDB (koleksi "files"), tanpa layanan penyimpanan luar.
APP_NAME = "perpus-smansa"
MAX_SIDE = 1080
TARGET_BYTES = 500 * 1024
MAX_UPLOAD = 25 * 1024 * 1024


def compress_photo(raw: bytes):
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
        img = ImageOps.exif_transpose(img)
    except Exception:
        raise HTTPException(400, "Berkas bukan foto yang valid. Gunakan JPG, PNG, WEBP, atau HEIC.")
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    out = b""
    for q in (90, 85, 80, 74, 68, 60):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        out = buf.getvalue()
        if len(out) <= TARGET_BYTES:
            break
    return out, img.size


async def photo_upload_allowed(db):
    """Izin unggah foto siswa mengikuti tombol "Foto siswa" (settings id=student_photo: enabled + until)."""
    doc = await db.settings.find_one({"id": "student_photo"}, {"_id": 0}) or {}
    if not doc.get("enabled", True):
        return False
    until = doc.get("until") or ""
    if until:
        try:
            u = datetime.fromisoformat(until.replace("Z", "+00:00"))
            if u.tzinfo is None:
                u = u.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= u:
                return False
        except ValueError:
            pass
    return True


def build_router(db, current_user):
    r = APIRouter()

    @r.post("/uploads/photo")
    async def upload_photo(file: UploadFile = File(...), user=Depends(current_user)):
        if user["role"] == "siswa" and not await photo_upload_allowed(db):
            raise HTTPException(403, "Unggah foto sedang ditutup oleh petugas perpustakaan")
        raw = await file.read()
        if not raw:
            raise HTTPException(400, "Berkas kosong")
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(400, "Ukuran foto maksimal 25MB")
        data, (w, h) = compress_photo(raw)
        path = f"{APP_NAME}/photos/{uuid.uuid4()}.jpg"
        try:
            await db.files.insert_one({"id": str(uuid.uuid4()), "storage_path": path, "data": data, "original_filename": file.filename, "original_size": len(raw), "content_type": "image/jpeg", "size": len(data), "width": w, "height": h, "uploaded_by": user["id"], "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
        except Exception as e:
            logger.error(f"Simpan foto gagal: {e}")
            raise HTTPException(500, "Foto gagal disimpan. Coba lagi.")
        return {"url": f"/api/files/{path}", "size": len(data), "original_size": len(raw), "width": w, "height": h}

    @r.get("/files/{path:path}")
    async def download(path: str, user=Depends(current_user)):
        record = await db.files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
        if not record or not record.get("data"):
            raise HTTPException(404, "Berkas tidak ditemukan")
        return Response(content=bytes(record["data"]), media_type=record.get("content_type", "image/jpeg"), headers={"Cache-Control": "private, max-age=86400"})

    return r
