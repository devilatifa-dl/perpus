import io, os, uuid, logging
from datetime import datetime, timezone
import requests
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()
logger = logging.getLogger("media")

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "perpus-smansa"
MAX_SIDE = 1080
TARGET_BYTES = 500 * 1024
MAX_UPLOAD = 25 * 1024 * 1024
_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _request(method, path, retry=True, **kw):
    resp = requests.request(method, f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(), **kw.pop("headers", {})}, **kw)
    if resp.status_code == 404 and retry and method == "PUT":
        init_storage(force=True)
        return _request(method, path, retry=False, **kw)
    resp.raise_for_status()
    return resp


def put_object(path, data, content_type):
    return _request("PUT", path, headers={"Content-Type": content_type}, data=data, timeout=120).json()


def get_object(path):
    resp = _request("GET", path, timeout=60)
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


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
    doc = await db.settings.find_one({"id": "main"}, {"_id": 0, "member_photo_upload": 1}) or {}
    return doc.get("member_photo_upload", True)


def build_router(db, current_user):
    r = APIRouter()

    @r.post("/uploads/photo")
    async def upload_photo(file: UploadFile = File(...), user=Depends(current_user)):
        if user["role"] == "siswa" and not await photo_upload_allowed(db):
            raise HTTPException(403, "Upload foto sedang ditutup admin")
        raw = await file.read()
        if not raw:
            raise HTTPException(400, "Berkas kosong")
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(400, "Ukuran foto maksimal 25MB")
        data, (w, h) = compress_photo(raw)
        path = f"{APP_NAME}/photos/{uuid.uuid4()}.jpg"
        try:
            result = put_object(path, data, "image/jpeg")
        except Exception as e:
            logger.error(f"Upload storage gagal: {e}")
            raise HTTPException(502, "Penyimpanan foto sedang bermasalah. Coba lagi.")
        await db.files.insert_one({"id": str(uuid.uuid4()), "storage_path": result["path"], "original_filename": file.filename, "original_size": len(raw), "content_type": "image/jpeg", "size": len(data), "width": w, "height": h, "uploaded_by": user["id"], "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
        return {"url": f"/api/files/{result['path']}", "size": len(data), "original_size": len(raw), "width": w, "height": h}

    @r.get("/files/{path:path}")
    async def download(path: str, user=Depends(current_user)):
        record = await db.files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
        if not record:
            raise HTTPException(404, "Berkas tidak ditemukan")
        data, _ = get_object(path)
        return Response(content=data, media_type=record.get("content_type", "image/jpeg"), headers={"Cache-Control": "private, max-age=86400"})

    return r
