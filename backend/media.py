import io, uuid, logging, base64
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()
logger = logging.getLogger("media")

# Foto disimpan langsung di MongoDB (koleksi "files"), tanpa layanan penyimpanan luar.
APP_NAME = "perpus-smansa"
MAX_SIDE = 1080
TARGET_BYTES = 600 * 1024
MAX_UPLOAD = 25 * 1024 * 1024


def compress_photo(raw: bytes, max_side: int = MAX_SIDE, target: int = TARGET_BYTES):
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
    # Foto JPEG yang sudah kecil & tidak perlu diputar disimpan apa adanya (tanpa kompres ulang → tidak menurun kualitasnya)
    try:
        src_fmt = (Image.open(io.BytesIO(raw)).format or "").upper()
        orient = Image.open(io.BytesIO(raw)).getexif().get(0x0112, 1)
    except Exception:
        src_fmt, orient = "", 1
    if src_fmt == "JPEG" and orient in (0, 1) and len(raw) <= target and max(img.size) <= max_side:
        return raw, img.size
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    out = b""
    for q in (94, 90, 86, 80, 74, 68, 60):
        buf = io.BytesIO()
        # kualitas tinggi tanpa chroma subsampling (4:4:4) agar tepi wajah/teks tetap tajam
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0 if q >= 86 else 2)
        out = buf.getvalue()
        if len(out) <= target:
            break
    return out, img.size


COVER_SIDE = 1000
COVER_TARGET = 400 * 1024


def shrink_data_url(value: str, max_side: int = COVER_SIDE, target: int = COVER_TARGET) -> str:
    """Sampul base64 dikompres di server bila masih besar (jaga-jaga bila browser tidak mengecilkannya)."""
    if not isinstance(value, str) or not value.startswith("data:image") or ";base64," not in value:
        return value
    try:
        raw = base64.b64decode(value.split(",", 1)[1])
        with Image.open(io.BytesIO(raw)) as probe:
            w, h = probe.size
        if len(raw) <= target and max(w, h) <= max_side:
            return value
        data, _ = compress_photo(raw, max_side, target)
    except Exception:
        return value
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


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
