from dotenv import load_dotenv
load_dotenv(override=False)

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, re, uuid, bcrypt, jwt, io, csv, json, logging, secrets, zlib, base64, asyncio
from collections import OrderedDict
from openpyxl import load_workbook
from media import photo_upload_allowed, shrink_data_url, build_router as media_router
from offline_sync import client_dt
from reports_pdf import WIB, build_loans, in_period, render_report_pdf, render_report_xlsx, fmt_long

ROOT_DIR = Path(__file__).parent
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]
app = FastAPI(title="Perpustakaan SMA Negeri 1 Abung Tengah")
api = APIRouter(prefix="/api")
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_NAME = "Devi Latifa, S.I.Pust"
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 characters")

class LoginInput(BaseModel):
    email: str
    password: str
    portal: str = "admin"

class BookInput(BaseModel):
    title: str
    author: str
    category: str = "Umum"
    shelf: str = "R-01"
    isbn: str = ""
    cover: str = ""
    stock: int = Field(1, ge=1, le=1000)

class BookUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=120)
    category: str = Field("Umum", max_length=60)
    shelf: str = Field(..., min_length=1, max_length=20)
    isbn: str = Field("", max_length=40)
    cover: str = ""

class ShelfInput(BaseModel):
    id: str = Field(..., pattern=r"^[A-Za-z0-9-]{1,12}$")
    name: str = Field(..., min_length=1, max_length=60)
    capacity: int = Field(..., ge=1, le=10000)
    color: str = Field("azure", max_length=20)

class StockInput(BaseModel):
    stock: int = Field(..., ge=0, le=5000)

class MemberInput(BaseModel):
    name: str
    student_id: str = ""
    class_name: str = ""
    photo: str = ""
    member_type: str = "siswa"   # "siswa" | "guru"
    subject: str = ""            # mata pelajaran (khusus guru)

GURU_CLASS = "Guru"

def normalize_member(doc: dict) -> dict:
    """Siswa: NIS + kelas. Guru: tanpa NIS/kelas, wajib mapel; kelas diisi "Guru"
    supaya daftar per kelas, cetak massal per kelas & laporan otomatis mengelompokkan guru."""
    t = (doc.get("member_type") or "siswa").strip().lower()
    if t not in ("siswa", "guru"): raise HTTPException(400, "Tipe anggota harus Siswa atau Guru")
    doc["member_type"] = t
    doc["name"] = (doc.get("name") or "").strip()
    if not doc["name"]: raise HTTPException(400, "Nama lengkap wajib diisi")
    if t == "guru":
        doc["subject"] = (doc.get("subject") or "").strip()
        if not doc["subject"]: raise HTTPException(400, "Mata pelajaran guru wajib diisi")
        doc["student_id"] = ""; doc["class_name"] = GURU_CLASS
    else:
        doc["subject"] = ""
        doc["student_id"] = (doc.get("student_id") or "").strip()
        doc["class_name"] = (doc.get("class_name") or "").strip()
        if not doc["class_name"]: raise HTTPException(400, "Kelas siswa wajib diisi")
        if doc["class_name"].lower() == GURU_CLASS.lower(): raise HTTPException(400, 'Kelas "Guru" khusus untuk anggota tipe Guru')
    return doc

class BulkDeleteInput(BaseModel):
    class_name: str

class PromoteInput(BaseModel):
    from_class: str
    to_class: str

class PhotoInput(BaseModel):
    photo: str = ""

class ResetInput(BaseModel):
    include_books: bool = False
    code: str = ""
    password: str = ""
    biometric_token: str = ""

class PasswordChangeInput(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class VerifyPasswordInput(BaseModel):
    password: str

class PasswordSetInput(BaseModel):
    new_password: str = Field(..., min_length=6)

class TransactionInput(BaseModel):
    member_id: str
    book_id: str
    action: str = "pinjam"
    # Diisi bila transaksi dicatat saat offline lalu disinkronkan
    client_id: str = Field("", max_length=64)
    client_time: str = Field("", max_length=40)

class IncomingInput(BaseModel):
    title: str
    author: str
    category: str = "Umum"
    shelf: str = "R-01"
    isbn: str = ""
    cover: str = ""
    quantity: int = Field(1, ge=1, le=200)
    date: str = ""
    source: str = ""

class StatusInput(BaseModel):
    status: str
    note: str = ""
    reporter: str = ""
    member_id: str = ""      # untuk "hilang saat dipinjam": siapa peminjamnya
    transaction_id: str = "" # transaksi pinjam yang ditutup

class CompensationInput(BaseModel):
    compensated: bool = True
    note: str = ""

CARD_TEXT_KEYS = {"school", "title", "owner", "name", "fields", "class", "nis", "address", "code", "back_title", "back_rules", "back_web"}
CARD_FONT_IDS = {"modern", "klasik", "elegan", "mono", "shrikhand", "orbitron", "chakrapetch", "rajdhani", "exo2", "audiowide"}

class SettingsInput(BaseModel):
    school_logo: str = ""
    library_logo: str = ""
    card_theme: str = "navy"
    card_layout: str = "classic"
    card_show_qr: bool = True
    card_show_address: bool = True
    card_title: str = "KARTU ANGGOTA PERPUSTAKAAN"
    card_school_name: str = "SMA NEGERI 1 ABUNG TENGAH"
    card_font: str = "modern"
    card_font_size: str = "sedang"
    card_school_spacing: float = 0
    card_school_logo_pos: str = "kiri"
    card_library_logo_pos: str = "kanan"
    card_photo_pos: str = "kiri"
    card_qr_pos: str = "atas"
    card_back_title: str = Field("PERATURAN & TATA TERTIB PERPUSTAKAAN", max_length=120)
    card_back_rules: str = Field("Kartu ini wajib dibawa setiap meminjam dan mengembalikan buku.\nKembalikan buku tepat waktu sesuai tanggal yang ditentukan petugas.\nJaga buku tetap bersih; dilarang melipat, mencoret, atau merobek.\nBuku yang hilang atau rusak wajib diganti dengan judul yang sama.\nKartu tidak boleh dipinjamkan kepada orang lain.\nJika kartu ini ditemukan, mohon kembalikan ke Perpustakaan SMANSA.", max_length=2000)
    card_back_web: str = Field("perpustakaan.sman1abungtengah.sch.id", max_length=150)
    # Teks yang bisa diubah di kartu & ukuran per teks (persen dari ukuran bawaan, 50-200)
    card_owner_label: str = Field("PEMILIK KARTU", max_length=40)
    card_class_label: str = Field("Kelas", max_length=20)
    card_nis_label: str = Field("NIS", max_length=20)
    card_address: str = Field("Jln Raya Subik, Desa Pekurun Selatan", max_length=120)
    card_text_sizes: Dict[str, int] = Field(default_factory=dict)
    # Jenis font per teks (kosong = ikut font kartu) + tampil/sembunyi baris
    card_text_fonts: Dict[str, str] = Field(default_factory=dict)
    card_show_class: bool = True
    card_show_nis: bool = True
    card_show_code: bool = True
    # Foto anggota di kartu: ukuran (persen), bentuk
    card_photo_size: int = Field(100, ge=60, le=160)
    card_photo_shape: str = "membulat"

    @field_validator("card_text_sizes")
    @classmethod
    def _clamp_sizes(cls, v):
        return {k: max(50, min(200, int(val))) for k, val in (v or {}).items() if k in CARD_TEXT_KEYS}

    @field_validator("card_text_fonts")
    @classmethod
    def _check_fonts(cls, v):
        return {k: val for k, val in (v or {}).items() if k in CARD_TEXT_KEYS and val in CARD_FONT_IDS}

    @field_validator("card_photo_shape")
    @classmethod
    def _check_shape(cls, v):
        return v if v in ("kotak", "membulat", "bulat") else "membulat"

    @field_validator("card_photo_pos")
    @classmethod
    def _check_photo_pos(cls, v):
        return v if v in ("kiri", "kanan", "atas") else "kiri"

DEFAULT_SETTINGS = SettingsInput().model_dump()

def staff_only(user):
    if user["role"] not in ["admin", "petugas"]: raise HTTPException(403, "Akses ditolak")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def public(doc):
    doc = dict(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc

def password_hash(value):
    return bcrypt.hashpw(value.encode(), bcrypt.gensalt()).decode()

def book_key(b):
    return (str(b.get("title", "")).strip().lower(), str(b.get("author", "")).strip().lower())

def compute_state(b):
    stock = max(int(b.get("stock") or 0), 0); borrowed = max(int(b.get("borrowed") or 0), 0); lost = max(int(b.get("lost") or 0), 0)
    borrowed = min(borrowed, stock)
    available = stock - borrowed
    status = "Tersedia" if available > 0 else ("Dipinjam" if borrowed > 0 else ("Hilang" if lost > 0 else "Habis"))
    return {"stock": stock, "borrowed": borrowed, "lost": lost, "available": available, "status": status}

async def refresh_book(book_id):
    doc = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not doc: return None
    state = compute_state(doc)
    await db.books.update_one({"id": book_id}, {"$set": state})
    return slim_book({**doc, **state})

# ---------- Sampul buku: dikirim terpisah sebagai gambar kecil (bukan teks base64 di daftar buku) ----------
def _cover_version(length, tail):
    return format(zlib.crc32(f"{length}:{tail}".encode()) & 0xFFFFFFFF, "08x")

def cover_ref(book_id, version, size="thumb"):
    return f"/api/books/{book_id}/cover?v={version}&s={size}"

def is_cover_ref(value):
    return isinstance(value, str) and value.startswith("/api/books/") and "/cover" in value

def real_cover(value):
    """Nilai sampul dari formulir: URL sampul kita sendiri berarti 'tidak berubah'."""
    return "" if is_cover_ref(value) else (value or "")

def slim_book(b):
    b = dict(b)
    c = b.get("cover") or ""
    if isinstance(c, str) and c.startswith("data:"):
        b["cover"] = cover_ref(b["id"], _cover_version(len(c), c[-48:]))
    return b

BOOK_LIST_STAGES = [
    {"$addFields": {"_c": {"$ifNull": ["$cover", ""]}}},
    {"$addFields": {"_c": {"$cond": [{"$eq": [{"$type": "$_c"}, "string"]}, "$_c", ""]}}},
    {"$addFields": {"_dc": {"$eq": [{"$substrCP": ["$_c", 0, 5]}, "data:"]}, "_len": {"$strLenCP": "$_c"}}},
    {"$addFields": {"_tail": {"$cond": ["$_dc", {"$substrCP": ["$_c", {"$max": [0, {"$subtract": ["$_len", 48]}]}, 48]}, ""]},
                    "cover": {"$cond": ["$_dc", "", "$_c"]}}},
    {"$project": {"_id": 0, "_c": 0}},
]

async def list_books_slim(match=None, limit=500):
    rows = await db.books.aggregate([{"$match": match or {}}, {"$sort": {"created_at": -1}}, {"$limit": limit}, *BOOK_LIST_STAGES]).to_list(limit)
    for b in rows:
        b.pop("_id", None)
        if b.pop("_dc", False):
            b["cover"] = cover_ref(b["id"], _cover_version(b.get("_len", 0), b.get("_tail", "")))
        b.pop("_len", None); b.pop("_tail", None)
    return rows

_cover_cache = OrderedDict()
_COVER_CACHE_MAX = 400

def _render_cover(data_url, size):
    head, _, b64 = data_url.partition(",")
    raw = base64.b64decode(b64)
    mime = head[5:].split(";")[0] or "image/jpeg"
    if size == "full":
        return raw, mime
    from PIL import Image
    im = Image.open(io.BytesIO(raw))
    im.thumbnail((300, 440))
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.convert("RGBA").split()[-1])
        im = bg
    out = io.BytesIO()
    im.convert("RGB").save(out, "JPEG", quality=74, optimize=True, progressive=True)
    return out.getvalue(), "image/jpeg"

async def find_same_book(title, author):
    key = (title.strip().lower(), author.strip().lower())
    rx = {"$regex": f"^\\s*{re.escape(title.strip())}\\s*$", "$options": "i"}
    for b in await db.books.find({"title": rx}, {"_id": 0}).to_list(50):
        if book_key(b) == key: return b
    return None

async def normalize_books():
    """Gabungkan buku berjudul & penulis sama menjadi satu judul dengan angka stok (idempoten)."""
    books = await db.books.find({}, {"_id": 0}).sort("created_at", 1).to_list(100000)
    groups = {}
    for b in books: groups.setdefault(book_key(b), []).append(b)
    for items in groups.values():
        if len(items) == 1 and "stock" in items[0] and "available" in items[0]: continue
        main = items[0]; stock = borrowed = lost = 0
        for b in items:
            if "stock" in b:
                stock += int(b.get("stock") or 0); borrowed += int(b.get("borrowed") or 0); lost += int(b.get("lost") or 0)
            else:
                st = b.get("status", "Tersedia")
                if st == "Hilang": lost += 1
                else:
                    stock += 1
                    if st == "Dipinjam": borrowed += 1
        extra = {"cover": next((b.get("cover") for b in items if b.get("cover")), ""), "isbn": next((b.get("isbn") for b in items if b.get("isbn")), "")}
        await db.books.update_one({"id": main["id"]}, {"$set": {**compute_state({"stock": stock, "borrowed": borrowed, "lost": lost}), **extra}})
        others = [b["id"] for b in items[1:]]
        if not others: continue
        await db.books.delete_many({"id": {"$in": others}})
        for coll in ("transactions", "reservations", "missing"):
            await db[coll].update_many({"book_id": {"$in": others}}, {"$set": {"book_id": main["id"]}})
        await db.missing.update_many({"code": {"$in": others}}, {"$set": {"code": main["id"]}})
        for inc in await db.incoming.find({"book_ids": {"$in": others}}, {"_id": 0, "id": 1, "book_ids": 1}).to_list(5000):
            ids = list(dict.fromkeys(main["id"] if i in others else i for i in inc.get("book_ids", [])))
            await db.incoming.update_one({"id": inc["id"]}, {"$set": {"book_ids": ids}})

async def open_loan_count(member_id, book_id):
    p = await db.transactions.count_documents({"member_id": member_id, "book_id": book_id, "action": "pinjam"})
    # "kembali" dan "hilang" sama-sama menutup pinjaman
    k = await db.transactions.count_documents({"member_id": member_id, "book_id": book_id, "action": {"$in": ["kembali", "hilang"]}})
    return p - k

async def take_copy(book_id):
    res = await db.books.find_one_and_update({"id": book_id, "$expr": {"$gt": ["$stock", "$borrowed"]}}, {"$inc": {"borrowed": 1}})
    if not res: raise HTTPException(400, "Stok buku habis — semua eksemplar sedang dipinjam")
    return await refresh_book(book_id)

async def return_copy(book_id):
    res = await db.books.find_one_and_update({"id": book_id, "borrowed": {"$gt": 0}}, {"$inc": {"borrowed": -1}})
    if not res: raise HTTPException(400, "Tidak ada eksemplar buku ini yang sedang dipinjam")
    return await refresh_book(book_id)

def token_for(user):
    return jwt.encode({"sub": user["id"], "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, JWT_SECRET, algorithm="HS256")

async def current_user(request: Request):
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Silakan masuk terlebih dahulu")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user: raise HTTPException(401, "Sesi tidak ditemukan")
        return user
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesi telah berakhir")

async def seed():
    if await db.users.count_documents({}) == 0:
        users = [
            {"id":"u-admin","name":ADMIN_NAME,"email":"admin@smansa.sch.id","role":"admin","password_hash":password_hash("admin123")},
            {"id":"u-petugas","name":"Pustakawan","email":"petugas@smansa.sch.id","role":"petugas","password_hash":password_hash("petugas123")},
            {"id":"u-siswa","name":"Bima Pratama","email":"siswa@smansa.sch.id","role":"siswa","student_id":"24001","password_hash":password_hash("siswa123")},
        ]
        await db.users.insert_many(users)
    # One-time content seed. Gated by meta flag so a manual data reset stays empty permanently.
    meta = await db.meta.find_one({"id": "seed"}, {"_id": 0})
    if not (meta and meta.get("done")):
        if await db.shelves.count_documents({}) == 0:
            await db.shelves.insert_many([{ "id":"R-01", "name":"Pengetahuan Umum", "color":"azure", "capacity":80 }, {"id":"R-02","name":"Sains & Teknologi","color":"mint","capacity":60},{"id":"R-03","name":"Bahasa & Sastra","color":"amber","capacity":50}])
        if await db.books.count_documents({}) == 0:
            await db.books.insert_many([
                {"id":"BK-1042","title":"Laskar Pelangi","author":"Andrea Hirata","category":"Sastra","shelf":"R-03","isbn":"9789793062792","cover":"https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=400&q=70","status":"Tersedia","created_at":now_iso()},
                {"id":"BK-1043","title":"Ensiklopedia Sains Remaja","author":"Tim Edukasi","category":"Sains","shelf":"R-02","isbn":"9786021234567","cover":"https://images.unsplash.com/photo-1532012197267-da84d127e765?auto=format&fit=crop&w=400&q=70","status":"Dipinjam","created_at":now_iso()},
                {"id":"BK-1044","title":"Matematika Dasar SMA","author":"D. Kurniawan","category":"Pelajaran","shelf":"R-01","isbn":"9786027654321","cover":"https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=400&q=70","status":"Tersedia","created_at":now_iso()},
                {"id":"BK-1045","title":"Bumi Manusia","author":"Pramoedya Ananta Toer","category":"Sastra","shelf":"R-03","isbn":"9789799731234","cover":"https://images.unsplash.com/photo-1476275466078-4007374efbbe?auto=format&fit=crop&w=400&q=70","status":"Tersedia","created_at":now_iso()},
            ])
            # Data contoh langsung memakai format stok (hanya menyentuh buku contoh yang baru dimasukkan)
            for bid, borrowed in (("BK-1042", 0), ("BK-1043", 1), ("BK-1044", 0), ("BK-1045", 0)):
                await db.books.update_one({"id": bid}, {"$set": compute_state({"stock": 1, "borrowed": borrowed, "lost": 0})})
        if await db.members.count_documents({}) == 0:
            await db.members.insert_many([{"id":"MB-2024001","name":"Bima Pratama","student_id":"24001","class_name":"XI IPA 2","photo":""},{"id":"MB-2024002","name":"Siti Rahma","student_id":"24002","class_name":"X IPS 1","photo":""},{"id":"MB-2024003","name":"Raka Wijaya","student_id":"24003","class_name":"XII IPA 1","photo":""}])
        if await db.transactions.count_documents({}) == 0:
            await db.transactions.insert_many([{ "id":"TRX-001","member_id":"MB-2024001","member_name":"Bima Pratama","book_id":"BK-1043","book_title":"Ensiklopedia Sains Remaja","action":"pinjam","date":(datetime.now(timezone.utc)-timedelta(days=10)).isoformat()},{"id":"TRX-002","member_id":"MB-2024002","member_name":"Siti Rahma","book_id":"BK-1042","book_title":"Laskar Pelangi","action":"kembali","date":now_iso()}])
        await db.meta.update_one({"id": "seed"}, {"$set": {"id": "seed", "done": True}}, upsert=True)
    # Migrasi data lama — dijalankan SEKALI saja (tidak menyentuh data produksi di setiap restart)
    if not await db.meta.find_one({"id": "legacy-migrations-v1"}):
        await db.members.update_many({}, {"$unset": {"email": "", "phone": ""}})
        await db.users.update_one({"id": "u-petugas", "name": "Rina Pustakawan"}, {"$set": {"name": "Pustakawan"}})
        for coll, field in (("incoming", "recorded_by"), ("missing", "reported_by"), ("reservations", "processed_by"), ("visits", "recorded_by"), ("visits", "checkout_by"), ("stocktake", "officer")):
            await db[coll].update_many({field: "Rina Pustakawan"}, {"$set": {field: "Pustakawan"}})
        await db.settings.update_many({"card_school_name": "SMA 1 NEGERI ABUNG TENGAH"}, {"$set": {"card_school_name": "SMA NEGERI 1 ABUNG TENGAH"}})
        # (penggabungan buku ganda hanya lewat pemulihan cadangan, tidak otomatis saat start)
        await db.users.update_one({"id":"u-siswa","student_id":{"$exists":False}},{"$set":{"student_id":"24001"}})
        await db.meta.update_one({"id": "legacy-migrations-v1"}, {"$set": {"id": "legacy-migrations-v1", "done": True}}, upsert=True)
    await db.users.update_one({"id": "u-admin", "name": "Administrator"}, {"$set": {"name": "Devi Latifa"}})
    # Gelar admin: "Devi Latifa" → "Devi Latifa, S.I.Pust" (sekali saja, juga di catatan petugas)
    if not await db.meta.find_one({"id": "admin-title-v1"}):
        await db.users.update_one({"id": "u-admin", "name": "Devi Latifa"}, {"$set": {"name": ADMIN_NAME}})
        for coll, field in (("incoming", "recorded_by"), ("missing", "reported_by"), ("reservations", "processed_by"), ("visits", "recorded_by"), ("visits", "checkout_by"), ("stocktake", "officer")):
            await db[coll].update_many({field: "Devi Latifa"}, {"$set": {field: ADMIN_NAME}})
        await db.meta.update_one({"id": "admin-title-v1"}, {"$set": {"id": "admin-title-v1", "done": True}}, upsert=True)

async def ensure_indexes():
    specs = {
        "visits": ["check_in", "date", "member_id", "client_id", "checkout_client_id", [("date", -1), ("member_id", 1)]],
        "members": ["id", "student_id", "name", "class_name"],
        "books": ["id", "title", "author", "shelf", "category", "status", "created_at", [("title", 1), ("author", 1)]],
        "transactions": ["id", "client_id", "member_id", "book_id", "date", "action", [("member_id", 1), ("book_id", 1)], [("action", 1), ("date", -1)]],
        "reservations": ["id", "member_id", "book_id", "status", "created_at"],
        "incoming": ["date", "book_ids"],
        "missing": ["date", "book_id", "status"],
        "stocktake": ["date"],
        "files": ["storage_path"],
        "restore_chunks": [[("upload_id", 1), ("idx", 1)]],
        "users": ["member_id", "role"],
        "login_attempts": ["identifier"],
    }
    for coll, keys in specs.items():
        for key in keys:
            try:
                await db[coll].create_index(key)
            except Exception as e:  # indeks hanya untuk kecepatan, jangan gagalkan start
                logging.getLogger(__name__).warning("Gagal membuat indeks %s.%s: %s", coll, key, e)

@app.on_event("startup")
async def startup():
    await seed()
    await db.users.create_index("email", unique=True)
    await ensure_indexes()

@api.get("/")
async def root(): return {"message":"Perpustakaan SMA Negeri 1 Abung Tengah aktif"}

@api.get("/health")
async def health():
    """Ping ringan untuk memastikan server sudah merespons normal (dipakai auto-reload saat server lambat)."""
    return {"ok": True, "ts": now_iso()}

@api.post("/auth/login")
async def login(data: LoginInput, response: Response):
    identifier = data.email.lower()
    attempt = await db.login_attempts.find_one({"identifier": identifier}, {"_id": 0})
    if attempt and attempt.get("locked_until", "") > now_iso():
        raise HTTPException(429, "Terlalu banyak percobaan. Coba lagi beberapa menit.")
    user = await db.users.find_one({"email": identifier}, {"_id": 0})
    if not user or not bcrypt.checkpw(data.password.encode(), user["password_hash"].encode()):
        failures = (attempt or {}).get("failures", 0) + 1
        payload = {"identifier": identifier, "failures": failures}
        if failures >= 5: payload["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": identifier}, {"$set": payload}, upsert=True)
        raise HTTPException(401, "Email atau kata sandi salah")
    await db.login_attempts.delete_one({"identifier": identifier})
    if data.portal == "siswa" and user["role"] != "siswa":
        raise HTTPException(403, "Akun petugas/admin harus masuk melalui portal /admin")
    if data.portal == "admin" and user["role"] == "siswa":
        raise HTTPException(403, "Akun siswa hanya dapat masuk melalui portal /siswa")
    token = token_for(user)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=28800, path="/")
    return {**public(user), "token": token}

@api.get("/auth/me")
async def me(user=Depends(current_user)): return public(user)

@api.post("/auth/verify-password")
async def verify_password(data: VerifyPasswordInput, user=Depends(current_user)):
    """Cek kata sandi akun yang sedang login — dipakai gerbang 'Akun & sandi'."""
    if not bcrypt.checkpw(data.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Kata sandi salah")
    return {"ok": True}

@api.post("/auth/logout")
async def logout(response: Response): response.delete_cookie("access_token", path="/", secure=True, samesite="none"); return {"ok":True}

@api.post("/account/password")
async def change_own_password(data: PasswordChangeInput, user=Depends(current_user)):
    staff_only(user)
    if not bcrypt.checkpw(data.current_password.encode(), user["password_hash"].encode()):
        raise HTTPException(400, "Kata sandi lama salah")
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": password_hash(data.new_password)}})
    return {"ok": True}

@api.get("/users")
async def list_users(user=Depends(current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Hanya admin yang dapat mengelola akun")
    rows = await db.users.find({"role": {"$in": ["admin", "petugas"]}}, {"_id":0}).to_list(100)
    return [public(r) for r in rows]

@api.put("/users/{user_id}/password")
async def set_user_password(user_id: str, data: PasswordSetInput, user=Depends(current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Hanya admin yang dapat mengubah kata sandi akun lain")
    target = await db.users.find_one({"id": user_id}, {"_id":0})
    if not target: raise HTTPException(404, "Akun tidak ditemukan")
    if target["role"] not in ["admin", "petugas"]: raise HTTPException(400, "Hanya akun admin/petugas yang dapat diubah di sini")
    await db.users.update_one({"id": user_id}, {"$set": {"password_hash": password_hash(data.new_password)}})
    return {"ok": True}

OVERDUE_DAYS = 3

async def overdue_loans():
    tx = await db.transactions.find({}, {"_id":0}).to_list(5000)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=OVERDUE_DAYS)).isoformat()
    now = datetime.now(timezone.utc)
    out = []
    for l in build_loans(tx):
        if l["status"] == "Dipinjam" and l["borrowed_at"] and l["borrowed_at"] < cutoff:
            days = (now - datetime.fromisoformat(l["borrowed_at"])).days
            out.append({**l, "days_out": days})
    out.sort(key=lambda l: -l["days_out"])
    return out

@api.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    incoming = await db.incoming.aggregate([{"$group":{"_id":None,"total":{"$sum":"$quantity"}}}]).to_list(1)
    overdue = len(await overdue_loans()) if user["role"] != "siswa" else 0
    waiting = await db.reservations.count_documents({"status":"Menunggu"}) if user["role"] != "siswa" else 0
    agg = await db.books.aggregate([{"$group":{"_id":None,"stock":{"$sum":"$stock"},"borrowed":{"$sum":"$borrowed"},"lost":{"$sum":"$lost"},"available":{"$sum":"$available"},"titles":{"$sum":1}}}]).to_list(1)
    a = agg[0] if agg else {"stock":0,"borrowed":0,"lost":0,"available":0,"titles":0}
    vis = {"visitors_today":0,"visitors_inside":0}
    if user["role"] != "siswa":
        await visits_auto_close()
        today = datetime.now(WIB).date().isoformat()
        vis = {"visitors_today": await db.visits.count_documents({"date": today}), "visitors_inside": await db.visits.count_documents({"date": today, "check_out": None})}
    return {**vis, "books":a["stock"],"titles":a["titles"],"available":a["available"],"members":await db.members.count_documents({}),"borrowed":a["borrowed"],"missing":a["lost"],"incoming":incoming[0]["total"] if incoming else 0,"transactions":await db.transactions.count_documents({}),"overdue":overdue,"reservations_waiting":waiting}

@api.get("/overdue")
async def overdue(user=Depends(current_user)):
    staff_only(user)
    return {"days": OVERDUE_DAYS, "items": await overdue_loans()}

def own_member_filter(user):
    if user.get("member_id"): return {"id": user["member_id"]}
    return {"$or": [{"student_id": user.get("student_id", "__none__")}, {"name": {"$regex": f"^{re.escape(user['name'])}$", "$options": "i"}}]}

@api.get("/account/member")
async def my_member(user=Depends(current_user)):
    if user["role"] != "siswa":
        return None
    return await db.members.find_one(own_member_filter(user), {"_id":0})

async def check_student_photo(user, photo, member_id=None):
    if user["role"] != "siswa": return
    if photo and not photo.startswith("/api/files/"): raise HTTPException(400, "Foto harus diunggah melalui tombol unggah")
    if member_id and user.get("member_id") and user["member_id"] != member_id: raise HTTPException(403, "Kamu hanya dapat mengubah fotomu sendiri")

@api.post("/account/photo")
async def set_my_photo(data: PhotoInput, user=Depends(current_user)):
    if user["role"] != "siswa":
        raise HTTPException(403, "Hanya siswa yang dapat mengubah fotonya sendiri")
    await check_student_photo(user, data.photo)
    member = await db.members.find_one(own_member_filter(user), {"_id":0})
    await check_student_photo_allowed(member)
    if member:
        await db.members.update_one({"id": member["id"]}, {"$set": {"photo": data.photo}})
        return await db.members.find_one({"id": member["id"]}, {"_id":0})
    # Belum terdaftar sebagai anggota: buat data anggota otomatis dari akun siswa
    doc = {"id": "MB-" + str(uuid.uuid4())[:8].upper(), "name": user["name"], "student_id": user.get("student_id", ""), "class_name": user.get("class_name", ""), "photo": data.photo}
    await db.members.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}

class ReservationInput(BaseModel):
    book_id: str
    member_id: str = ""

class ProcessInput(BaseModel):
    action: str

@api.get("/reservations")
async def reservations(user=Depends(current_user)):
    staff_only(user)
    rows = await db.reservations.find({}, {"_id":0}).sort("created_at", -1).to_list(500)
    rows.sort(key=lambda r: (r["status"] != "Menunggu", r["created_at"] if r["status"] != "Menunggu" else ""), reverse=False)
    return rows

@api.get("/reservations/mine")
async def my_reservations(member_id: str = "", user=Depends(current_user)):
    if member_id and not user.get("member_id"):
        member = await db.members.find_one({"id": member_id}, {"_id":0})
    else:
        member = await db.members.find_one(own_member_filter(user), {"_id":0})
    if not member: return []
    return await db.reservations.find({"member_id": member["id"]}, {"_id":0}).sort("created_at", -1).to_list(100)

@api.post("/reservations")
async def reserve(data: ReservationInput, user=Depends(current_user)):
    if data.member_id and not user.get("member_id"):
        member = await db.members.find_one({"id": data.member_id}, {"_id":0})
    else:
        member = await db.members.find_one(own_member_filter(user), {"_id":0})
    if not member: raise HTTPException(404, "Data keanggotaan belum terdaftar. Hubungi petugas perpustakaan.")
    book = await db.books.find_one({"id": data.book_id}, {"_id":0})
    if not book: raise HTTPException(404, "Buku tidak ditemukan")
    if int(book.get("stock") or 0) <= 0: raise HTTPException(400, "Stok buku ini kosong, tidak bisa dipesan")
    if await db.reservations.find_one({"book_id": book["id"], "member_id": member["id"], "status": "Menunggu"}):
        raise HTTPException(400, "Kamu sudah memesan buku ini")
    if await db.reservations.count_documents({"member_id": member["id"], "status": "Menunggu"}) >= 3:
        raise HTTPException(400, "Maksimal 3 pesanan aktif")
    doc = {"id":"RS-"+str(uuid.uuid4())[:8].upper(),"book_id":book["id"],"book_title":book["title"],"book_shelf":book["shelf"],"member_id":member["id"],"member_name":member["name"],"class_name":member["class_name"],"status":"Menunggu","created_at":now_iso(),"processed_at":None,"processed_by":None}
    await db.reservations.insert_one(doc); return public(doc)

@api.delete("/reservations/{res_id}")
async def cancel_reservation(res_id: str, member_id: str = "", user=Depends(current_user)):
    res = await db.reservations.find_one({"id": res_id}, {"_id":0})
    if not res: raise HTTPException(404, "Pesanan tidak ditemukan")
    if user["role"] == "siswa":
        if member_id and not user.get("member_id"):
            if member_id != res["member_id"]: raise HTTPException(403, "Bukan pesanan anggota ini")
        else:
            member = await db.members.find_one(own_member_filter(user), {"_id":0})
            if not member or member["id"] != res["member_id"]: raise HTTPException(403, "Bukan pesanan Anda")
    if res["status"] != "Menunggu": raise HTTPException(400, "Pesanan sudah diproses")
    await db.reservations.update_one({"id": res_id}, {"$set": {"status":"Dibatalkan","processed_at":now_iso(),"processed_by":user["name"]}})
    return {"ok": True}

@api.post("/reservations/{res_id}/process")
async def process_reservation(res_id: str, data: ProcessInput, user=Depends(current_user)):
    staff_only(user)
    res = await db.reservations.find_one({"id": res_id}, {"_id":0})
    if not res or res["status"] != "Menunggu": raise HTTPException(404, "Pesanan menunggu tidak ditemukan")
    if data.action == "pinjam":
        book = await db.books.find_one({"id": res["book_id"]}, {"_id":0})
        if not book: raise HTTPException(404, "Buku tidak ditemukan")
        if await open_loan_count(res["member_id"], book["id"]) > 0: raise HTTPException(400, "Anggota ini masih meminjam buku yang sama")
        await take_copy(book["id"])
        rm = await db.members.find_one({"id": res["member_id"]}, {"_id":0, "class_name":1}) or {}
        await db.transactions.insert_one({"id":"TRX-"+str(uuid.uuid4())[:8].upper(),"member_id":res["member_id"],"member_name":res["member_name"],"class_name":rm.get("class_name",""),"book_id":book["id"],"book_title":book["title"],"action":"pinjam","date":now_iso(),"reservation_id":res_id})
        status = "Dipinjamkan"
    elif data.action == "tolak": status = "Ditolak"
    else: raise HTTPException(400, "Aksi tidak valid")
    await db.reservations.update_one({"id": res_id}, {"$set": {"status":status,"processed_at":now_iso(),"processed_by":user["name"]}})
    return {"ok": True, "status": status}

class StocktakeInput(BaseModel):
    shelf: str
    scanned: List[str] = []
    unscanned: List[str] = []
    misplaced: List[str] = []

@api.get("/stocktake")
async def stocktake_list(user=Depends(current_user)):
    staff_only(user)
    return await db.stocktake.find({}, {"_id":0}).sort("date", -1).to_list(50)

@api.post("/stocktake")
async def stocktake_save(data: StocktakeInput, user=Depends(current_user)):
    staff_only(user)
    doc = {"id":"SO-"+str(uuid.uuid4())[:8].upper(), **data.model_dump(), "scanned_count":len(data.scanned), "unscanned_count":len(data.unscanned), "misplaced_count":len(data.misplaced), "date":now_iso(), "by":user["name"]}
    await db.stocktake.insert_one(doc); return public(doc)

@api.get("/settings")
async def get_settings(user=Depends(current_user)):
    doc = await db.settings.find_one({"id":"main"}, {"_id":0,"id":0})
    return {**DEFAULT_SETTINGS, "member_photo_upload": True, **(doc or {})}

class PhotoToggleInput(BaseModel):
    enabled: bool

@api.put("/settings/photo-upload")
async def put_photo_upload(data: PhotoToggleInput, user=Depends(current_user)):
    staff_only(user)
    await db.settings.update_one({"id":"main"}, {"$set": {"member_photo_upload": data.enabled}}, upsert=True)
    return {"member_photo_upload": data.enabled}

@api.put("/settings")
async def put_settings(data: SettingsInput, user=Depends(current_user)):
    staff_only(user)
    await db.settings.update_one({"id":"main"}, {"$set": data.model_dump()}, upsert=True)
    return data.model_dump()

# ===== Izin unggah foto oleh siswa (diatur admin/petugas) =====
class StudentPhotoConfig(BaseModel):
    enabled: bool = True
    until: str = ""            # ISO datetime; kosong = tanpa batas waktu
    allow_replace: bool = True # boleh mengganti foto yang sudah ada

async def student_photo_config():
    doc = await db.settings.find_one({"id": "student_photo"}, {"_id": 0, "id": 0}) or {}
    cfg = {**StudentPhotoConfig().model_dump(), **doc}
    open_now = bool(cfg["enabled"])
    if open_now and cfg.get("until"):
        try:
            until = datetime.fromisoformat(cfg["until"].replace("Z", "+00:00"))
            if until.tzinfo is None: until = until.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= until:
                open_now = False
        except ValueError:
            pass
    # Unggah foto selalu dibuka (tombol on/off dihapus); penggantian foto hanya oleh admin
    cfg.update({"open": True, "enabled": True, "until": "", "allow_replace": False, "admin_only_replace": True})
    return cfg

async def check_student_photo_allowed(member):
    """Tombol on/off foto sudah dihapus: siswa/guru (dan petugas) boleh unggah SEKALI.
    Setelah foto ada, hanya admin yang dapat menggantinya."""
    if member and (member.get("photo") or "").strip():
        raise HTTPException(403, "Foto sudah diunggah. Hanya admin yang dapat mengganti foto anggota")

@api.get("/settings/student-photo")
async def get_student_photo(user=Depends(current_user)):
    return await student_photo_config()

@api.put("/settings/student-photo")
async def put_student_photo(data: StudentPhotoConfig, user=Depends(current_user)):
    staff_only(user)
    doc = data.model_dump()
    if doc["until"]:
        try:
            u = datetime.fromisoformat(doc["until"].replace("Z", "+00:00"))
            if u.tzinfo is None: u = u.replace(tzinfo=timezone.utc)
            doc["until"] = u.astimezone(timezone.utc).isoformat()
        except ValueError:
            raise HTTPException(400, "Format batas waktu tidak valid")
    doc["updated_by"] = user["name"]; doc["updated_at"] = now_iso()
    await db.settings.update_one({"id": "student_photo"}, {"$set": doc}, upsert=True)
    return await student_photo_config()

@api.get("/books")
async def books(user=Depends(current_user)):
    rows = await list_books_slim()
    waiting = {r["_id"]: r["n"] for r in await db.reservations.aggregate([{"$match":{"status":"Menunggu"}},{"$group":{"_id":"$book_id","n":{"$sum":1}}}]).to_list(500)}
    for b in rows: b["waiting"] = waiting.get(b["id"], 0)
    return rows

@api.get("/books/{book_id}/cover")
async def book_cover(book_id: str, v: str = "", s: str = "thumb"):
    """Gambar sampul (publik, tanpa data sensitif). URL memuat versi -> aman di-cache lama oleh browser/HP."""
    size = "full" if s == "full" else "thumb"
    key = (book_id, v, size)
    hit = _cover_cache.get(key) if v else None
    if not hit:
        doc = await db.books.find_one({"id": book_id}, {"_id": 0, "cover": 1})
        c = (doc or {}).get("cover") or ""
        if not isinstance(c, str) or not c.startswith("data:"):
            raise HTTPException(404, "Sampul tidak ditemukan")
        try:
            hit = await asyncio.to_thread(_render_cover, c, size)
        except Exception:
            raise HTTPException(404, "Sampul tidak dapat dibaca")
        if v:
            _cover_cache[key] = hit
            while len(_cover_cache) > _COVER_CACHE_MAX: _cover_cache.popitem(last=False)
    else:
        _cover_cache.move_to_end(key)
    body, mime = hit
    cache = "public, max-age=31536000, immutable" if v else "public, max-age=300"
    return Response(content=body, media_type=mime, headers={"Cache-Control": cache})

@api.post("/books")
async def add_book(data: BookInput, user=Depends(current_user)):
    if user["role"] == "siswa": raise HTTPException(403,"Siswa tidak dapat menambah buku")
    data.cover = await asyncio.to_thread(shrink_data_url, real_cover(data.cover))
    same = await find_same_book(data.title, data.author)
    if same:
        await db.books.update_one({"id": same["id"]}, {"$inc": {"stock": data.stock}, **({"$set": {"cover": data.cover}} if data.cover and not same.get("cover") else {})})
        return {**(await refresh_book(same["id"])), "merged": True, "added": data.stock}
    doc = data.model_dump(); doc.update({"id":"BK-"+str(uuid.uuid4())[:8].upper(),"created_at":now_iso(),"borrowed":0,"lost":0}); doc.update(compute_state(doc))
    await db.books.insert_one(doc); return {**slim_book(public(doc)), "merged": False, "added": data.stock}

@api.put("/books/{book_id}")
async def update_book(book_id: str, data: BookUpdate, user=Depends(current_user)):
    staff_only(user)
    book = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not book: raise HTTPException(404, "Buku tidak ditemukan")
    if not await db.shelves.find_one({"id": data.shelf}): raise HTTPException(400, "Rak tidak ditemukan")
    title, author = data.title.strip(), data.author.strip()
    same = await find_same_book(title, author)
    if same and same["id"] != book_id: raise HTTPException(400, f"Judul & penulis ini sudah ada ({same['id']}). Gunakan Atur stok untuk menambah eksemplar.")
    upd = {"title": title, "author": author, "category": data.category.strip() or "Umum", "shelf": data.shelf, "isbn": data.isbn.strip(), "updated_at": now_iso()}
    if not is_cover_ref(data.cover): upd["cover"] = await asyncio.to_thread(shrink_data_url, data.cover or "")  # URL sampul kita sendiri = sampul tidak diubah
    await db.books.update_one({"id": book_id}, {"$set": upd})
    if title != book["title"]:
        await db.transactions.update_many({"book_id": book_id}, {"$set": {"book_title": title}})
        await db.reservations.update_many({"book_id": book_id}, {"$set": {"book_title": title}})
        await db.missing.update_many({"book_id": book_id}, {"$set": {"title": title}})
    if data.shelf != book.get("shelf"):
        await db.reservations.update_many({"book_id": book_id, "status": "Menunggu"}, {"$set": {"book_shelf": data.shelf}})
    return await refresh_book(book_id)

@api.patch("/books/{book_id}/stock")
async def set_book_stock(book_id: str, data: StockInput, user=Depends(current_user)):
    staff_only(user)
    book = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not book: raise HTTPException(404, "Buku tidak ditemukan")
    if data.stock < int(book.get("borrowed") or 0): raise HTTPException(400, f"Stok tidak boleh kurang dari jumlah yang sedang dipinjam ({book.get('borrowed', 0)})")
    await db.books.update_one({"id": book_id}, {"$set": {"stock": data.stock}})
    return await refresh_book(book_id)

@api.delete("/books/{book_id}")
async def delete_book(book_id: str, user=Depends(current_user)):
    staff_only(user)
    result = await db.books.delete_one({"id":book_id})
    if result.deleted_count == 0: raise HTTPException(404, "Buku tidak ditemukan")
    return {"ok":True}

@api.patch("/books/{book_id}/status")
async def book_status(book_id: str, data: StatusInput, user=Depends(current_user)):
    staff_only(user)
    if data.status not in ["Hilang", "Tersedia"]: raise HTTPException(400, "Status tidak valid")
    book = await db.books.find_one({"id":book_id}, {"_id":0})
    if not book: raise HTTPException(404, "Buku tidak ditemukan")
    if data.status == "Hilang":
        # Dua jalur: eksemplar di rak (opname) atau eksemplar yang sedang dipinjam lalu dinyatakan hilang.
        if data.member_id:
            return await mark_lost_while_borrowed(book, data, user)
        res = await db.books.find_one_and_update({"id": book_id, "$expr": {"$gt": ["$stock", "$borrowed"]}}, {"$inc": {"stock": -1, "lost": 1}})
        if not res: raise HTTPException(400, "Tidak ada eksemplar di rak yang bisa ditandai hilang")
        await refresh_book(book_id)
        report = {"id":"LS-"+str(uuid.uuid4())[:8].upper(),"book_id":book_id,"title":book["title"],"code":book_id,"detail":data.note or "1 eksemplar","date":now_iso(),"status":"Hilang","reported_by":data.reporter.strip() or user["name"],"source":"rak","compensated":False}
        await db.missing.insert_one(report); return public(report)
    res = await db.books.find_one_and_update({"id": book_id, "lost": {"$gt": 0}}, {"$inc": {"stock": 1, "lost": -1}})
    if not res: raise HTTPException(400, "Tidak ada eksemplar buku ini yang tercatat hilang")
    await refresh_book(book_id)
    first = await db.missing.find_one({"book_id": book_id, "status": "Hilang"}, {"_id": 0}, sort=[("date", 1)])
    if first: await db.missing.update_one({"id": first["id"]}, {"$set": {"status": "Ditemukan", "found_at": now_iso()}})
    return {"ok":True, "status":"Tersedia"}

async def mark_lost_while_borrowed(book, data: StatusInput, user):
    """Eksemplar yang sedang dipinjam dinyatakan hilang: tutup pinjaman, pindahkan stok ke hilang, catat laporan."""
    member = await db.members.find_one({"id": data.member_id}, {"_id":0})
    if not member: raise HTTPException(404, "Anggota tidak ditemukan")
    if await open_loan_count(member["id"], book["id"]) <= 0:
        raise HTTPException(400, "Anggota ini tidak sedang meminjam buku tersebut")
    # Tutup pinjaman: borrowed -1, lalu pindahkan eksemplar ke hilang (stock -1, lost +1)
    res = await db.books.find_one_and_update({"id": book["id"], "borrowed": {"$gt": 0}}, {"$inc": {"borrowed": -1, "stock": -1, "lost": 1}})
    if not res: raise HTTPException(400, "Tidak ada eksemplar buku ini yang sedang dipinjam")
    await refresh_book(book["id"])
    when = now_iso()
    trx = {"id":"TRX-"+str(uuid.uuid4())[:8].upper(),"member_id":member["id"],"member_name":member["name"],"class_name":member.get("class_name",""),"book_id":book["id"],"book_title":book["title"],"action":"hilang","date":when,"note":data.note or "Dinyatakan hilang saat dipinjam"}
    if data.transaction_id: trx["loan_id"] = data.transaction_id
    await db.transactions.insert_one(trx)
    report = {"id":"LS-"+str(uuid.uuid4())[:8].upper(),"book_id":book["id"],"title":book["title"],"code":book["id"],"detail":data.note or "Hilang saat dipinjam","date":when,"status":"Hilang","reported_by":data.reporter.strip() or user["name"],"source":"pinjam","member_id":member["id"],"member_name":member["name"],"class_name":member.get("class_name",""),"transaction_id":trx["id"],"compensated":False}
    await db.missing.insert_one(report)
    return public(report)

@api.patch("/missing/{report_id}/compensation")
async def set_compensation(report_id: str, data: CompensationInput, user=Depends(current_user)):
    """Tandai ganti rugi buku hilang: sudah diganti atau belum."""
    staff_only(user)
    rep = await db.missing.find_one({"id": report_id}, {"_id":0})
    if not rep: raise HTTPException(404, "Laporan tidak ditemukan")
    upd = {"compensated": bool(data.compensated), "compensated_at": now_iso() if data.compensated else None, "compensated_by": user["name"] if data.compensated else None}
    if data.note: upd["compensation_note"] = data.note.strip()[:300]
    await db.missing.update_one({"id": report_id}, {"$set": upd})
    return {"ok": True, **upd}

@api.patch("/missing/{report_id}/found")
async def mark_missing_found(report_id: str, user=Depends(current_user)):
    """Buku hilang ditemukan kembali: kembalikan eksemplar ke rak dan tutup laporan."""
    staff_only(user)
    rep = await db.missing.find_one({"id": report_id}, {"_id":0})
    if not rep: raise HTTPException(404, "Laporan tidak ditemukan")
    if rep.get("status") == "Ditemukan": raise HTTPException(400, "Laporan ini sudah ditandai ditemukan")
    res = await db.books.find_one_and_update({"id": rep["book_id"], "lost": {"$gt": 0}}, {"$inc": {"stock": 1, "lost": -1}})
    if not res: raise HTTPException(400, "Tidak ada eksemplar buku ini yang tercatat hilang")
    await refresh_book(rep["book_id"])
    await db.missing.update_one({"id": report_id}, {"$set": {"status": "Ditemukan", "found_at": now_iso(), "found_by": user["name"]}})
    return {"ok": True, "status": "Ditemukan"}

@api.get("/incoming")
async def incoming_list(user=Depends(current_user)):
    staff_only(user)
    return await db.incoming.find({}, {"_id":0}).sort("date",-1).to_list(200)

@api.post("/incoming")
async def add_incoming(data: IncomingInput, user=Depends(current_user)):
    staff_only(user)
    date = data.date or now_iso()[:10]
    data.cover = await asyncio.to_thread(shrink_data_url, real_cover(data.cover))
    same = await find_same_book(data.title, data.author)
    if same:
        await db.books.update_one({"id": same["id"]}, {"$inc": {"stock": data.quantity}, **({"$set": {"cover": data.cover}} if data.cover and not same.get("cover") else {})})
        book = await refresh_book(same["id"]); merged = True
    else:
        base = data.model_dump(exclude={"quantity","date","source"})
        book = {**base, "id":"BK-"+str(uuid.uuid4())[:8].upper(), "stock": data.quantity, "borrowed": 0, "lost": 0, "created_at":now_iso()}; book.update(compute_state(book))
        await db.books.insert_one(book); merged = False
    doc = {"id":"IN-"+str(uuid.uuid4())[:8].upper(),"title":data.title,"author":data.author,"category":data.category,"shelf":data.shelf,"quantity":data.quantity,"detail":f"{data.quantity} eksemplar","source":data.source,"date":date,"status":"Tersimpan","book_ids":[book["id"]],"book_id":book["id"],"merged":merged,"stock_after":book["stock"],"recorded_by":user["name"],"created_at":now_iso()}
    await db.incoming.insert_one(doc); return public(doc)

@api.get("/members")
async def members(user=Depends(current_user)):
    staff_only(user)
    return await db.members.find({}, {"_id":0}).to_list(None)

@api.get("/members/options")
async def member_options(user=Depends(current_user)):
    rows = await db.members.find({}, {"_id":0,"id":1,"name":1,"class_name":1,"student_id":1,"photo":1,"member_type":1,"subject":1}).to_list(None)
    rows.sort(key=lambda m: (m.get("class_name",""), m.get("name","")))
    return rows

@api.post("/members")
async def add_member(data: MemberInput, user=Depends(current_user)):
    if user["role"] == "siswa": raise HTTPException(403,"Siswa tidak dapat menambah anggota")
    doc=normalize_member(data.model_dump())
    await ensure_unique_nis(doc["student_id"])
    doc.update({"id":"MB-"+str(uuid.uuid4())[:8].upper()}); await db.members.insert_one(doc); return public(doc)

async def ensure_unique_nis(sid: str, exclude_id: str = None):
    if not sid: return
    q = {"student_id": sid}
    if exclude_id: q["id"] = {"$ne": exclude_id}
    other = await db.members.find_one(q, {"_id": 0, "name": 1, "class_name": 1})
    if other: raise HTTPException(400, f"NIS {sid} sudah dipakai {other.get('name','anggota lain')} ({other.get('class_name','-')})")

def _cell_text(c):
    if c is None:
        return ""
    if isinstance(c, float) and c.is_integer():
        c = int(c)
    return str(c).strip()

def _parse_member_rows(filename: str, content: bytes):
    name_l = (filename or "").lower()
    rows = []
    if name_l.endswith(".xlsx"):
        try:
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception:
            raise HTTPException(400, "Berkas Excel tidak dapat dibaca. Pastikan format .xlsx yang valid.")
        ws = wb.active
        headers = None
        for row in ws.iter_rows(values_only=True):
            if headers is None:
                cand = [str(c).strip().lower() if c is not None else "" for c in row]
                # Lewati baris judul/petunjuk sampai menemukan baris kolom "nama"
                if not ({"nama", "name", "nama lengkap", "nama_lengkap"} & set(cand)):
                    continue
                headers = cand
                continue
            d = {}
            for i, c in enumerate(row):
                if i < len(headers) and headers[i]:
                    d[headers[i]] = _cell_text(c)
            if any(d.values()):
                rows.append(d)
        if headers is None:
            raise HTTPException(400, "Kolom 'nama' tidak ditemukan. Gunakan template Excel dari tombol Unduh template.")
    elif name_l.endswith(".xls"):
        raise HTTPException(400, "Format .xls lama belum didukung. Di Excel pilih Simpan Sebagai → Excel Workbook (.xlsx).")
    else:
        raise HTTPException(400, "Format tidak didukung. Gunakan berkas Excel (.xlsx)")
    return rows

@api.get("/members/import-template.xlsx")
async def member_import_template(user=Depends(current_user)):
    staff_only(user)
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    wb = Workbook(); ws = wb.active; ws.title = "Anggota"
    thin = Side(style="thin", color="CBD5E1"); border = Border(left=thin, right=thin, top=thin, bottom=thin)
    headers = ["nama", "nis", "kelas"]
    for j, h in enumerate(headers, start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="0F2745")
        c.alignment = Alignment(horizontal="center", vertical="center"); c.border = border
    samples = [("Budi Santoso", "24100", "X IPA 1"), ("Siti Aminah", "24101", "X IPA 1"), ("Rudi Hartono", "24102", "X IPS 2")]
    for i, r in enumerate(samples, start=2):
        for j, v in enumerate(r, start=1):
            c = ws.cell(row=i, column=j, value=v); c.border = border
            if j == 2: c.number_format = "@"
    for row in range(2, 2002):
        ws.cell(row=row, column=2).number_format = "@"  # NIS sebagai teks (angka 0 di depan tidak hilang)
    ws.column_dimensions["A"].width = 32; ws.column_dimensions["B"].width = 16; ws.column_dimensions["C"].width = 14
    ws.row_dimensions[1].height = 22; ws.freeze_panes = "A2"
    info = wb.create_sheet("Petunjuk")
    for i, t in enumerate([
        "PETUNJUK IMPOR ANGGOTA — PERPUSTAKAAN SMA NEGERI 1 ABUNG TENGAH",
        "1. Isi data di lembar 'Anggota'. Jangan ubah judul kolom: nama, nis, kelas.",
        "2. Satu baris = satu anggota. Boleh banyak kelas dalam satu berkas.",
        "3. Hapus 3 baris contoh (Budi, Siti, Rudi) sebelum mengimpor.",
        "4. NIS yang sudah terdaftar TIDAK dibuat baru: kelasnya diperbarui (kenaikan kelas).",
        "   NIS tidak boleh ganda dalam satu berkas.",
        "5. Simpan sebagai .xlsx lalu unggah di menu Anggota → Impor.",
    ], start=1):
        c = info.cell(row=i, column=1, value=t)
        if i == 1: c.font = Font(bold=True, color="0F2745", size=12)
    info.column_dimensions["A"].width = 80
    buf = io.BytesIO(); wb.save(buf)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="template-anggota.xlsx"'})

def _pick(d, *keys):
    for k in keys:
        if d.get(k):
            return d[k]
    return ""

async def freeze_old_class(member_ids, old_class: str):
    """Sebelum kelas anggota diganti: kunci kelas lama di riwayat yang belum mencatat kelas,
    agar laporan lama tetap memakai kelas saat transaksi terjadi."""
    if not member_ids or not (old_class or "").strip(): return
    empty = {"$or": [{"class_name": {"$exists": False}}, {"class_name": ""}, {"class_name": None}]}
    flt = {"member_id": {"$in": list(member_ids)}, **empty}
    await db.transactions.update_many(flt, {"$set": {"class_name": old_class}})
    await db.visits.update_many(flt, {"$set": {"class_name": old_class}})

@api.post("/members/import")
async def import_members(file: UploadFile = File(...), user=Depends(current_user)):
    staff_only(user)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "Ukuran berkas maksimal 5MB")
    rows = _parse_member_rows(file.filename or "", content)
    if not rows:
        raise HTTPException(400, "Berkas kosong atau tidak memiliki data")
    if len(rows) > 2000:
        raise HTTPException(400, "Maksimal 2000 baris per impor")
    all_members = await db.members.find({"member_type": {"$ne": "guru"}}, {"_id": 0, "id": 1, "name": 1, "student_id": 1, "class_name": 1}).to_list(None)
    by_nis = {}
    for m in all_members:
        sid = (m.get("student_id") or "").strip()
        if sid:
            by_nis.setdefault(sid, []).append(m)
    seen, matched_ids = set(), set()
    to_insert, updates, errors, skipped, unchanged = [], [], [], 0, 0
    for idx, d in enumerate(rows, start=2):
        name = _pick(d, "nama", "name", "nama lengkap", "nama_lengkap").strip()
        sid = _pick(d, "nis", "student_id", "nomor induk", "no induk", "nomor_induk", "no_induk").strip()
        cls = _pick(d, "kelas", "class_name", "class", "rombel").strip()
        reason = None
        if not cls or (not name and sid not in by_nis):
            reason = "Nama atau kelas kosong"
        elif sid and sid in seen:
            reason = f"NIS {sid} ganda di dalam berkas"
        if reason:
            skipped += 1
            errors.append({"row": idx, "nama": name, "nis": sid, "kelas": cls, "alasan": reason})
            continue
        if sid:
            seen.add(sid)
        if sid and sid in by_nis:
            # Sudah terdaftar: ID anggota (dan QR kartu) tetap, hanya kelas yang disesuaikan
            for m in by_nis[sid]:
                matched_ids.add(m["id"])
                if (m.get("class_name") or "").strip() != cls:
                    updates.append({"id": m["id"], "name": m.get("name", ""), "nis": sid, "from": m.get("class_name", ""), "to": cls})
                else:
                    unchanged += 1
            continue
        to_insert.append({"id": "MB-" + str(uuid.uuid4())[:8].upper(), "name": name, "student_id": sid, "class_name": cls, "photo": ""})
    if to_insert:
        await db.members.insert_many(to_insert)
    for u in updates:
        await freeze_old_class([u["id"]], u["from"])
        await db.members.update_one({"id": u["id"]}, {"$set": {"class_name": u["to"]}})
        await db.users.update_many({"member_id": u["id"], "role": "siswa"}, {"$set": {"class_name": u["to"]}})
        await db.reservations.update_many({"member_id": u["id"], "status": "Menunggu"}, {"$set": {"class_name": u["to"]}})
    not_in_file = [{"id": m["id"], "name": m.get("name", ""), "nis": m.get("student_id", ""), "kelas": m.get("class_name", "")}
                   for m in all_members if m["id"] not in matched_ids]
    not_in_file.sort(key=lambda x: (x["kelas"], x["name"]))
    return {"imported": len(to_insert), "updated": len(updates), "unchanged": unchanged, "skipped": skipped, "total": len(rows),
            "errors": errors, "class_changes": updates, "not_in_file": not_in_file}

class FailedRow(BaseModel):
    row: int
    nama: str = ""
    nis: str = ""
    kelas: str = ""
    alasan: str = ""

@api.post("/members/import-failed.xlsx")
async def import_failed_xlsx(rows: List[FailedRow], user=Depends(current_user)):
    staff_only(user)
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook(); ws = wb.active; ws.title = "Gagal diimpor"
    ws.append(["nama", "nis", "kelas", "alasan", "baris asal"])
    for c in ws[1]: c.font = Font(bold=True)
    for r in rows: ws.append([r.nama, r.nis, r.kelas, r.alasan, r.row])
    for col, w in zip("ABCDE", (32, 16, 12, 36, 11)): ws.column_dimensions[col].width = w
    buf = io.BytesIO(); wb.save(buf)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="anggota-gagal-impor.xlsx"'})

@api.put("/members/{member_id}")
async def update_member(member_id: str, data: MemberInput, user=Depends(current_user)):
    staff_only(user)
    member = await db.members.find_one({"id": member_id}, {"_id":0})
    if not member: raise HTTPException(404, "Anggota tidak ditemukan")
    upd = normalize_member(data.model_dump())
    # Foto yang sudah ada hanya boleh diganti/dihapus oleh admin
    if user["role"] != "admin" and member.get("photo") and (upd.get("photo") or "") != member.get("photo"):
        raise HTTPException(403, "Foto anggota sudah ada. Hanya admin yang dapat mengganti foto")
    await ensure_unique_nis(upd["student_id"], member_id)
    if (member.get("class_name") or "") != upd["class_name"]:
        await freeze_old_class([member_id], member.get("class_name", ""))
        await db.users.update_many({"member_id": member_id, "role": "siswa"}, {"$set": {"class_name": upd["class_name"]}})
    await db.members.update_one({"id": member_id}, {"$set": upd})
    updated = await db.members.find_one({"id": member_id}, {"_id":0})
    return updated

@api.post("/members/{member_id}/photo")
async def set_member_photo(member_id: str, data: PhotoInput, user=Depends(current_user)):
    await check_student_photo(user, data.photo, member_id)
    member = await db.members.find_one({"id": member_id}, {"_id":0})
    if not member: raise HTTPException(404, "Anggota tidak ditemukan")
    if user["role"] != "admin":
        await check_student_photo_allowed(member)
    await db.members.update_one({"id": member_id}, {"$set": {"photo": data.photo}})
    return await db.members.find_one({"id": member_id}, {"_id":0})

@api.post("/members/promote")
async def promote_members(data: PromoteInput, user=Depends(current_user)):
    staff_only(user)
    from_c = data.from_class.strip()
    to_c = data.to_class.strip()
    if not from_c or not to_c:
        raise HTTPException(400, "Kelas asal dan kelas tujuan wajib diisi")
    if from_c == to_c:
        raise HTTPException(400, "Kelas asal dan tujuan tidak boleh sama")
    if GURU_CLASS.lower() in (from_c.lower(), to_c.lower()):
        raise HTTPException(400, "Anggota guru tidak ikut naik kelas")
    count = await db.members.count_documents({"class_name": from_c})
    if count == 0:
        raise HTTPException(404, "Tidak ada anggota pada kelas asal tersebut")
    ids = [m["id"] for m in await db.members.find({"class_name": from_c}, {"_id": 0, "id": 1}).to_list(None)]
    await freeze_old_class(ids, from_c)
    result = await db.members.update_many({"class_name": from_c}, {"$set": {"class_name": to_c}})
    await db.users.update_many({"member_id": {"$in": ids}, "role": "siswa"}, {"$set": {"class_name": to_c}})
    return {"ok": True, "moved": result.modified_count, "from_class": from_c, "to_class": to_c}

@api.post("/members/bulk-delete")
async def bulk_delete_members(data: BulkDeleteInput, user=Depends(current_user)):
    staff_only(user)
    members = await db.members.find({"class_name": data.class_name}, {"_id":0,"id":1}).to_list(None)
    ids = [m["id"] for m in members]
    if not ids: raise HTTPException(404, "Tidak ada anggota pada kelas tersebut")
    await db.reservations.update_many({"member_id": {"$in": ids}, "status": "Menunggu"}, {"$set": {"status":"Dibatalkan","processed_at":now_iso(),"processed_by":user["name"]}})
    result = await db.members.delete_many({"id": {"$in": ids}})
    await db.users.delete_many({"member_id": {"$in": ids}, "role": "siswa"})
    return {"ok": True, "deleted": result.deleted_count, "class_name": data.class_name}

@api.delete("/members/{member_id}")
async def delete_member(member_id: str, user=Depends(current_user)):
    staff_only(user)
    result = await db.members.delete_one({"id": member_id})
    if result.deleted_count == 0: raise HTTPException(404, "Anggota tidak ditemukan")
    await db.users.delete_many({"member_id": member_id, "role": "siswa"})
    await db.reservations.update_many({"member_id": member_id, "status": "Menunggu"}, {"$set": {"status":"Dibatalkan","processed_at":now_iso(),"processed_by":user["name"]}})
    return {"ok": True}

@api.post("/admin/reset-data")
async def reset_data(data: ResetInput, user=Depends(current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Hanya admin yang dapat mereset data")
    # Fingerprint (WebAuthn) lebih dulu; kata sandi jadi cadangan bila tidak tersedia.
    if not await consume_biometric_token(db, user["id"], data.biometric_token):
        if not data.password or not bcrypt.checkpw(data.password.encode(), user["password_hash"].encode()):
            raise HTTPException(400, "Sandi admin salah. Data tidak direset.")
    members = (await db.members.delete_many({})).deleted_count
    await db.users.delete_many({"role": "siswa", "member_id": {"$exists": True}})
    transactions = (await db.transactions.delete_many({})).deleted_count
    incoming = (await db.incoming.delete_many({})).deleted_count
    missing = (await db.missing.delete_many({})).deleted_count
    reservations = (await db.reservations.delete_many({})).deleted_count
    stocktake = (await db.stocktake.delete_many({})).deleted_count
    if data.include_books:
        books = (await db.books.delete_many({})).deleted_count
    else:
        books = 0
        await db.books.update_many({}, [{"$set": {"stock": {"$add": [{"$ifNull": ["$stock", 0]}, {"$ifNull": ["$lost", 0]}]}, "lost": 0, "borrowed": 0}}, {"$set": {"available": "$stock", "status": {"$cond": [{"$gt": ["$stock", 0]}, "Tersedia", "Habis"]}}}])
    await db.visits.delete_many({})
    await db.meta.update_one({"id": "seed"}, {"$set": {"id": "seed", "done": True}}, upsert=True)
    return {"ok": True, "deleted": {"members": members, "transactions": transactions, "incoming": incoming, "missing": missing, "reservations": reservations, "stocktake": stocktake, "books": books}, "books_deleted": data.include_books}

BACKUP_COLLECTIONS = ["books", "members", "transactions", "incoming", "missing", "reservations", "stocktake", "shelves", "settings", "visits"]

@api.get("/admin/backup")
async def backup_data(user=Depends(current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Hanya admin yang dapat mengunduh cadangan data")
    dump = {}
    for name in BACKUP_COLLECTIONS:
        dump[name] = await db[name].find({}, {"_id": 0}).to_list(100000)
    return {"app": "perpustakaan-sma1-abung-tengah", "version": 1, "generated_at": now_iso(), "collections": dump}

BACKUP_REPORTS = [("transaksi", "01-Laporan-Transaksi"), ("masuk", "02-Laporan-Buku-Masuk"), ("hilang", "03-Laporan-Buku-Hilang"), ("kunjungan", "04-Laporan-Pengunjung")]

@api.get("/admin/backup.zip")
async def backup_zip(user=Depends(current_user)):
    """Cadangan lengkap: data (JSON, bisa dipulihkan) + semua laporan siap baca (Excel & PDF)."""
    if user["role"] != "admin": raise HTTPException(403, "Hanya admin yang dapat mengunduh cadangan data")
    import zipfile
    payload = await backup_data(user)
    now = datetime.now(WIB); stamp = now.strftime("%Y-%m-%d")
    jobs, notes = [], []
    for kind, name in BACKUP_REPORTS:
        rows, settings, _ = await export_rows(kind, "semua")
        jobs.append((f"laporan/{name}", kind, "semua", rows, settings, len(rows)))
    lb_months = (await visit_leaderboard(None, limit=1))["months"]
    for month in lb_months:
        lb, settings, _ = await export_rows("peringkat", month)
        if lb["total_visits"] == 0 and month != now.strftime("%Y-%m"):
            continue
        jobs.append((f"laporan/05-Peringkat-Rajin-Berkunjung/Peringkat-{month}", "peringkat", lb["label"], lb, settings, len(lb["students"])))
    loan_months = (await loan_leaderboard(None, limit=1))["months"]
    for month in loan_months:
        lb, settings, _ = await export_rows("peringkat-pinjam", month)
        if lb["total_loans"] == 0 and month != now.strftime("%Y-%m"):
            continue
        jobs.append((f"laporan/06-Peringkat-Rajin-Meminjam/Peringkat-{month}", "peringkat-pinjam", lb["label"], lb, settings, len(lb["students"])))
    # Peringkat khusus guru (hanya bulan yang ada aktivitas guru)
    for month in lb_months:
        lb, settings, _ = await export_rows("peringkat", month, "guru")
        if lb["total_visits"]:
            jobs.append((f"laporan/07-Peringkat-Guru-Berkunjung/Peringkat-Guru-{month}", "peringkat", lb["label"], lb, settings, len(lb["students"])))
    for month in loan_months:
        lb, settings, _ = await export_rows("peringkat-pinjam", month, "guru")
        if lb["total_loans"]:
            jobs.append((f"laporan/08-Peringkat-Guru-Meminjam/Peringkat-Guru-{month}", "peringkat-pinjam", lb["label"], lb, settings, len(lb["students"])))

    def build():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("data-cadangan.json", json.dumps(payload, ensure_ascii=False, indent=2, default=str))
            for path, kind, period, rows, settings, count in jobs:
                for ext, render in (("xlsx", render_report_xlsx), ("pdf", render_report_pdf)):
                    try:
                        z.writestr(f"{path}.{ext}", render(kind, period, rows, settings, user["name"]))
                    except Exception as e:
                        logging.getLogger(__name__).warning("Laporan %s.%s gagal dibuat: %s", path, ext, e)
                        notes.append(f"- {path}.{ext} gagal dibuat")
                notes_line = f"- {path}.xlsx / .pdf ({count} baris)"
                notes.append(notes_line)
            readme = [
                "CADANGAN PERPUSTAKAAN SMA NEGERI 1 ABUNG TENGAH",
                f"Dibuat: {fmt_long(now, True)} WIB oleh {user['name']}",
                "",
                "data-cadangan.json  -> berkas untuk menu 'Pulihkan data' (boleh juga unggah ZIP ini langsung).",
                "laporan/            -> laporan siap baca (Excel & PDF), semua periode:",
                *notes,
            ]
            z.writestr("BACA-SAYA.txt", "\n".join(readme))
        return buf.getvalue()

    data = await asyncio.to_thread(build)
    return Response(content=data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="backup-perpustakaan-{stamp}.zip"', "X-Backup-Bytes": str(len(data)), "Cache-Control": "no-store, no-transform"})

# Pemulihan data dari cadangan: lihat restore_big.py (tanpa batas ukuran, unggah bertahap).


@api.get("/members/{member_id}/history")
async def member_history(member_id: str, user=Depends(current_user)):
    staff_only(user)
    member = await db.members.find_one({"id":member_id}, {"_id":0})
    if not member: raise HTTPException(404, "Anggota tidak ditemukan")
    return await history_for(member)

@api.get("/account/history")
async def my_history(user=Depends(current_user)):
    if user["role"] != "siswa" or not user.get("member_id"): raise HTTPException(403, "Riwayat hanya untuk akun anggota")
    member = await db.members.find_one({"id": user["member_id"]}, {"_id":0})
    if not member: raise HTTPException(404, "Data anggota tidak ditemukan")
    return await history_for(member)

class MemberAccountInput(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field("", max_length=100)

@api.get("/members/{member_id}/account")
async def get_member_account(member_id: str, user=Depends(current_user)):
    staff_only(user)
    acc = await db.users.find_one({"member_id": member_id, "role": "siswa"}, {"_id":0, "password_hash":0})
    return acc

@api.put("/members/{member_id}/account")
async def set_member_account(member_id: str, data: MemberAccountInput, user=Depends(current_user)):
    staff_only(user)
    member = await db.members.find_one({"id": member_id}, {"_id":0})
    if not member: raise HTTPException(404, "Anggota tidak ditemukan")
    email = data.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email): raise HTTPException(400, "Format email tidak valid")
    acc = await db.users.find_one({"member_id": member_id, "role": "siswa"}, {"_id":0})
    other = await db.users.find_one({"email": email}, {"_id":0})
    if other and (not acc or other["id"] != acc["id"]): raise HTTPException(400, "Email sudah dipakai akun lain")
    if data.password and len(data.password) < 6: raise HTTPException(400, "Kata sandi minimal 6 karakter")
    upd = {"email": email, "name": member["name"], "student_id": member.get("student_id", ""), "class_name": member.get("class_name", "")}
    if data.password: upd["password_hash"] = password_hash(data.password)
    if acc:
        await db.users.update_one({"id": acc["id"]}, {"$set": upd})
    else:
        if not data.password: raise HTTPException(400, "Kata sandi wajib diisi untuk akun baru")
        await db.users.insert_one({"id": "u-" + str(uuid.uuid4())[:8], "role": "siswa", "member_id": member_id, **upd})
    return await db.users.find_one({"member_id": member_id, "role": "siswa"}, {"_id":0, "password_hash":0})

@api.delete("/members/{member_id}/account")
async def delete_member_account(member_id: str, user=Depends(current_user)):
    staff_only(user)
    res = await db.users.delete_one({"member_id": member_id, "role": "siswa"})
    if res.deleted_count == 0: raise HTTPException(404, "Anggota ini belum punya akun")
    return {"ok": True}

async def history_for(member):
    member_id = member["id"]
    tx = await db.transactions.find({"member_id":member_id}, {"_id":0}).sort("date",1).to_list(300)
    history = []
    for t in tx:
        if t["action"] == "pinjam": history.append({**t, "returned": False, "returned_at": None})
        else:
            for h in reversed(history):
                if h["book_id"] == t["book_id"] and not h["returned"]: h.update(returned=True, returned_at=t["date"]); break
    history.reverse()
    active = sum(1 for h in history if not h["returned"])
    return {"member":member,"history":history,"total":len(history),"active":active}

@api.get("/shelves")
async def shelves(user=Depends(current_user)): return await db.shelves.find({}, {"_id":0}).sort("id", 1).to_list(200)

@api.post("/shelves")
async def add_shelf(data: ShelfInput, user=Depends(current_user)):
    staff_only(user)
    sid = data.id.strip().upper()
    if await db.shelves.find_one({"id": sid}): raise HTTPException(400, f"Kode rak {sid} sudah dipakai")
    doc = {"id": sid, "name": data.name.strip(), "capacity": data.capacity, "color": data.color, "created_at": now_iso()}
    await db.shelves.insert_one(doc); return public(doc)

@api.put("/shelves/{shelf_id}")
async def update_shelf(shelf_id: str, data: ShelfInput, user=Depends(current_user)):
    staff_only(user)
    shelf = await db.shelves.find_one({"id": shelf_id}, {"_id": 0})
    if not shelf: raise HTTPException(404, "Rak tidak ditemukan")
    new_id = data.id.strip().upper()
    if new_id != shelf_id and await db.shelves.find_one({"id": new_id}): raise HTTPException(400, f"Kode rak {new_id} sudah dipakai")
    await db.shelves.update_one({"id": shelf_id}, {"$set": {"id": new_id, "name": data.name.strip(), "capacity": data.capacity, "color": data.color, "updated_at": now_iso()}})
    moved = 0
    if new_id != shelf_id:
        moved = (await db.books.update_many({"shelf": shelf_id}, {"$set": {"shelf": new_id}})).modified_count
        await db.incoming.update_many({"shelf": shelf_id}, {"$set": {"shelf": new_id}})
        await db.stocktake.update_many({"shelf": shelf_id}, {"$set": {"shelf": new_id}})
        await db.reservations.update_many({"book_shelf": shelf_id}, {"$set": {"book_shelf": new_id}})
    return {**(await db.shelves.find_one({"id": new_id}, {"_id": 0})), "books_updated": moved}

@api.delete("/shelves/{shelf_id}")
async def delete_shelf(shelf_id: str, move_to: str = "", user=Depends(current_user)):
    staff_only(user)
    if not await db.shelves.find_one({"id": shelf_id}): raise HTTPException(404, "Rak tidak ditemukan")
    if await db.shelves.count_documents({}) <= 1: raise HTTPException(400, "Minimal harus ada satu rak")
    count = await db.books.count_documents({"shelf": shelf_id})
    if count:
        if not move_to: raise HTTPException(400, f"Rak masih berisi {count} judul buku. Pilih rak tujuan untuk memindahkannya.")
        if move_to == shelf_id or not await db.shelves.find_one({"id": move_to}): raise HTTPException(400, "Rak tujuan tidak valid")
        await db.books.update_many({"shelf": shelf_id}, {"$set": {"shelf": move_to}})
        await db.reservations.update_many({"book_shelf": shelf_id, "status": "Menunggu"}, {"$set": {"book_shelf": move_to}})
    await db.shelves.delete_one({"id": shelf_id})
    return {"ok": True, "moved": count, "move_to": move_to or None}

@api.get("/transactions")
async def transactions(user=Depends(current_user)):
    staff_only(user)
    return await db.transactions.find({}, {"_id":0}).sort("date",-1).to_list(200)

@api.post("/transactions")
async def transaction(data: TransactionInput, user=Depends(current_user)):
    staff_only(user)
    if data.client_id:
        dup = await db.transactions.find_one({"client_id": data.client_id}, {"_id":0})
        if dup: return {**public(dup), "duplicate": True}
    member=await db.members.find_one({"id":data.member_id},{"_id":0}); book=await db.books.find_one({"id":data.book_id},{"_id":0})
    if not member or not book: raise HTTPException(404,"Anggota atau buku tidak ditemukan")
    action=data.action
    if action not in ("pinjam","kembali"): raise HTTPException(400,"Aksi tidak valid")
    open_count = await open_loan_count(member["id"], book["id"])
    if action=="pinjam":
        if open_count > 0: raise HTTPException(400,"Anggota ini masih meminjam buku yang sama")
        await take_copy(book["id"])
    else:
        if open_count <= 0: raise HTTPException(400,"Anggota ini tidak sedang meminjam buku ini")
        await return_copy(book["id"])
    when = client_dt(data.client_time)
    doc={"id":"TRX-"+str(uuid.uuid4())[:8].upper(),"member_id":member["id"],"member_name":member["name"],"class_name":member.get("class_name",""),"book_id":book["id"],"book_title":book["title"],"action":action,"date":when.isoformat() if when else now_iso()}
    if data.client_id: doc["client_id"] = data.client_id
    if when: doc["offline"] = True; doc["synced_at"] = now_iso()
    await db.transactions.insert_one(doc); return public(doc)

@api.get("/reports")
async def reports(user=Depends(current_user)):
    staff_only(user)
    tx=await db.transactions.find({}, {"_id":0}).sort("date",-1).to_list(500)
    incoming=await db.incoming.find({}, {"_id":0}).sort("date",-1).to_list(200)
    missing=await db.missing.find({}, {"_id":0}).sort("date",-1).to_list(200)
    return {"transactions":tx,"loans":await attach_class(build_loans(tx)),"incoming":incoming,"missing":missing}

async def attach_class(loans):
    """Lengkapi kelas peminjam: pakai kelas saat transaksi, atau kelas anggota sekarang untuk transaksi lama."""
    ids = list({l["member_id"] for l in loans if not l.get("class_name") and l.get("member_id")})
    info = {m["id"]: m.get("class_name", "") for m in await db.members.find({"id": {"$in": ids}}, {"_id":0, "id":1, "class_name":1}).to_list(100000)} if ids else {}
    for l in loans:
        if not l.get("class_name"): l["class_name"] = info.get(l.get("member_id"), "")
    return loans

OVERDUE_DAYS = 3

async def overdue_report(period: str = "semua", now=None):
    """Daftar peminjaman yang sudah dipinjam lebih dari OVERDUE_DAYS hari dan belum dikembalikan."""
    now = now or datetime.now(WIB)
    loans = await attach_class(build_loans(await db.transactions.find({}, {"_id":0}).to_list(100000)))
    rows = []
    for l in loans:
        if l.get("status") != "Dipinjam" or not l.get("borrowed_at"): continue
        try:
            dt = datetime.fromisoformat(l["borrowed_at"].replace("Z", "+00:00"))
        except ValueError:
            continue
        dt = dt.astimezone(WIB) if dt.tzinfo else dt
        days = (now.date() - dt.date()).days
        if days <= OVERDUE_DAYS: continue
        rows.append({**l, "days_out": days, "borrowed_date": dt.date().isoformat()})
    rows.sort(key=lambda r: r["days_out"], reverse=True)
    if period in ("harian", "bulanan"):
        rows = [r for r in rows if in_period(r["borrowed_at"], period, now)]
    total_days = sum(r["days_out"] for r in rows)
    per_class = {}
    for r in rows:
        key = r.get("class_name") or "-"
        per_class[key] = per_class.get(key, 0) + 1
    n = len(rows) or 1
    classes = [{"class_name": k, "count": v, "pct": v * 100 / n} for k, v in sorted(per_class.items(), key=lambda x: -x[1])]
    return {
        "days": OVERDUE_DAYS,
        "total": len(rows),
        "avg_days": round(total_days / n, 1) if rows else 0,
        "max_days": max((r["days_out"] for r in rows), default=0),
        "items": rows,
        "per_class": classes,
    }

@api.get("/reports/overdue")
async def reports_overdue(period: str = "semua", user=Depends(current_user)):
    staff_only(user)
    return await overdue_report(period)

async def export_rows(type: str, period: str, audience: str = "siswa"):
    if type not in ("transaksi","masuk","hilang","kunjungan","statistik","peringkat","peringkat-pinjam","terlambat"): raise HTTPException(400, "Jenis laporan tidak valid")
    now = datetime.now(WIB)
    settings = await db.settings.find_one({"id":"main"}, {"_id":0}) or {}
    if type == "terlambat":
        return await overdue_report(period, now), settings, now
    if type == "peringkat-pinjam":
        return await loan_leaderboard(period if re.match(r"^\d{4}-\d{2}$", period or "") else None, limit=50, audience=audience), settings, now
    if type == "peringkat":
        await visits_auto_close()
        return await visit_leaderboard(period if re.match(r"^\d{4}-\d{2}$", period or "") else None, limit=50, audience=audience), settings, now
    if type in ("kunjungan","statistik"):
        await visits_auto_close()
        if type == "statistik":
            return await visit_stats(period), settings, now
        rows = await db.visits.find({}, {"_id":0}).sort("check_in",-1).to_list(100000)
        return [r for r in rows if in_visit_period(r.get("check_in"), period, now)], settings, now
    if type == "transaksi":
        rows = await attach_class(build_loans(await db.transactions.find({}, {"_id":0}).to_list(100000)))
    elif type == "masuk":
        rows = await db.incoming.find({}, {"_id":0}).sort("date",-1).to_list(100000)
    else:
        rows = await db.missing.find({}, {"_id":0}).sort("date",-1).to_list(100000)
    rows = [r for r in rows if in_period(r.get("date"), period, now)]
    return rows, settings, now

@api.get("/reports/export.pdf")
async def export_report(type: str = "transaksi", period: str = "semua", orientation: str = "landscape", audience: str = "siswa", user=Depends(current_user)):
    staff_only(user)
    orientation = "portrait" if orientation == "portrait" else "landscape"
    rows, settings, now = await export_rows(type, period, audience)
    if type in ("peringkat", "peringkat-pinjam") and rows.get("audience") == "guru": type_label = f"{type}-guru"
    else: type_label = type
    pdf = render_report_pdf(type, rows["label"] if type in ("peringkat", "peringkat-pinjam") else period, rows, settings, user["name"], orientation=orientation)
    filename = f"laporan-{type_label}-{period}-{'potret' if orientation == 'portrait' else 'lanskap'}-{now.strftime('%Y%m%d')}.pdf"
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@api.get("/reports/export.xlsx")
async def export_report_xlsx(type: str = "transaksi", period: str = "semua", orientation: str = "landscape", audience: str = "siswa", user=Depends(current_user)):
    staff_only(user)
    orientation = "portrait" if orientation == "portrait" else "landscape"
    rows, settings, now = await export_rows(type, period, audience)
    type_label = f"{type}-guru" if type in ("peringkat", "peringkat-pinjam") and rows.get("audience") == "guru" else type
    data = render_report_xlsx(type, rows["label"] if type in ("peringkat", "peringkat-pinjam") else period, rows, settings, user["name"], orientation=orientation)
    filename = f"laporan-{type_label}-{period}-{'potret' if orientation == 'portrait' else 'lanskap'}-{now.strftime('%Y%m%d')}.xlsx"
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

from visits import build_router, visits_auto_close, visit_stats, in_visit_period, visit_leaderboard
api.include_router(build_router(db, current_user, staff_only, now_iso))
from summary import build_router as summary_router
from loan_rank import build_router as loan_rank_router, loan_leaderboard
from restore_big import build_router as restore_router
api.include_router(restore_router(db, current_user, None, normalize_books, BACKUP_COLLECTIONS))  # tanpa kode email
api.include_router(loan_rank_router(db, current_user))
from purge import build_router as purge_router
api.include_router(purge_router(db, current_user, None, visits_auto_close))  # tanpa kode email
from webauthn_auth import build_router as webauthn_router, consume_biometric_token
api.include_router(webauthn_router(db, current_user))
api.include_router(media_router(db, current_user))
api.include_router(summary_router(db, current_user, staff_only, overdue_loans, visits_auto_close))
app.include_router(api)
# CORS sepenuhnya dari env: FRONTEND_URL + CORS_ORIGINS (dipisah koma, "*" = semua asal) + CORS_ORIGIN_REGEX (opsional)
_cors_all = [o.strip().rstrip("/") for o in (os.environ.get("FRONTEND_URL", "") + "," + os.environ.get("CORS_ORIGINS", "")).split(",") if o.strip()]
_cors = [o for o in _cors_all if o != "*"]
_cors_regex = ".*" if "*" in _cors_all else (os.environ.get("CORS_ORIGIN_REGEX", "").strip() or None)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=_cors, allow_origin_regex=_cors_regex, allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition", "X-Backup-Bytes"])

class SelectiveGZip:
    """Kompres respons JSON/teks (data jauh lebih kecil di HP). Berkas yang sudah terkompresi (ZIP, PDF, Excel, gambar) dilewati."""
    SKIP = re.compile(r"(\.zip|\.pdf|\.xlsx|/cover$|/files/|/restore/)")
    def __init__(self, app):
        self.app = app
        self.gz = GZipMiddleware(app, minimum_size=800, compresslevel=6)
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not self.SKIP.search(scope.get("path", "")):
            return await self.gz(scope, receive, send)
        return await self.app(scope, receive, send)

app.add_middleware(SelectiveGZip)

@app.on_event("shutdown")
async def shutdown(): client.close()