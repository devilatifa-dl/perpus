from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, re, uuid, bcrypt, jwt
from reports_pdf import WIB, build_loans, in_period, render_report_pdf, render_report_xlsx

ROOT_DIR = Path(__file__).parent
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]
app = FastAPI(title="Perpustakaan SMA 1 Negeri Abung Tengah")
api = APIRouter(prefix="/api")
JWT_SECRET = os.environ["JWT_SECRET"]
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
    status: str = "Tersedia"

class MemberInput(BaseModel):
    name: str
    student_id: str
    class_name: str
    photo: str = ""

class BulkDeleteInput(BaseModel):
    class_name: str

class ResetInput(BaseModel):
    include_books: bool = False

class PasswordChangeInput(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class PasswordSetInput(BaseModel):
    new_password: str = Field(..., min_length=6)

class TransactionInput(BaseModel):
    member_id: str
    book_id: str
    action: str = "pinjam"

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

class SettingsInput(BaseModel):
    school_logo: str = ""
    library_logo: str = ""
    card_theme: str = "navy"
    card_layout: str = "classic"
    card_show_qr: bool = True
    card_show_address: bool = True
    card_title: str = "KARTU ANGGOTA PERPUSTAKAAN"
    card_font: str = "modern"
    card_school_spacing: float = 0
    card_logo_pos: str = "kiri"
    card_photo_pos: str = "kiri"
    card_qr_pos: str = "atas"

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
            {"id":"u-admin","name":"Administrator","email":"admin@smansa.sch.id","role":"admin","password_hash":password_hash("admin123")},
            {"id":"u-petugas","name":"Rina Pustakawan","email":"petugas@smansa.sch.id","role":"petugas","password_hash":password_hash("petugas123")},
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
        if await db.members.count_documents({}) == 0:
            await db.members.insert_many([{"id":"MB-2024001","name":"Bima Pratama","student_id":"24001","class_name":"XI IPA 2","photo":""},{"id":"MB-2024002","name":"Siti Rahma","student_id":"24002","class_name":"X IPS 1","photo":""},{"id":"MB-2024003","name":"Raka Wijaya","student_id":"24003","class_name":"XII IPA 1","photo":""}])
        if await db.transactions.count_documents({}) == 0:
            await db.transactions.insert_many([{ "id":"TRX-001","member_id":"MB-2024001","member_name":"Bima Pratama","book_id":"BK-1043","book_title":"Ensiklopedia Sains Remaja","action":"pinjam","date":(datetime.now(timezone.utc)-timedelta(days=10)).isoformat()},{"id":"TRX-002","member_id":"MB-2024002","member_name":"Siti Rahma","book_id":"BK-1042","book_title":"Laskar Pelangi","action":"kembali","date":now_iso()}])
        await db.meta.update_one({"id": "seed"}, {"$set": {"id": "seed", "done": True}}, upsert=True)
    await db.members.update_many({}, {"$unset": {"email": "", "phone": ""}})
    await db.users.update_one({"id":"u-siswa","student_id":{"$exists":False}},{"$set":{"student_id":"24001"}})

@app.on_event("startup")
async def startup():
    await seed()

@api.get("/")
async def root(): return {"message":"Perpustakaan SMA 1 Negeri Abung Tengah aktif"}

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
    response.set_cookie("access_token", token_for(user), httponly=True, samesite="lax", max_age=28800)
    return public(user)

@api.get("/auth/me")
async def me(user=Depends(current_user)): return public(user)

@api.post("/auth/logout")
async def logout(response: Response): response.delete_cookie("access_token"); return {"ok":True}

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

OVERDUE_DAYS = 7

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
    return {"books":await db.books.count_documents({}),"members":await db.members.count_documents({}),"borrowed":await db.books.count_documents({"status":"Dipinjam"}),"missing":await db.books.count_documents({"status":"Hilang"}),"incoming":incoming[0]["total"] if incoming else 0,"transactions":await db.transactions.count_documents({}),"overdue":overdue,"reservations_waiting":waiting}

@api.get("/overdue")
async def overdue(user=Depends(current_user)):
    staff_only(user)
    return {"days": OVERDUE_DAYS, "items": await overdue_loans()}

def own_member_filter(user):
    return {"$or": [{"student_id": user.get("student_id", "__none__")}, {"name": {"$regex": f"^{re.escape(user['name'])}$", "$options": "i"}}]}

class ReservationInput(BaseModel):
    book_id: str

class ProcessInput(BaseModel):
    action: str

@api.get("/reservations")
async def reservations(user=Depends(current_user)):
    staff_only(user)
    rows = await db.reservations.find({}, {"_id":0}).sort("created_at", -1).to_list(500)
    rows.sort(key=lambda r: (r["status"] != "Menunggu", r["created_at"] if r["status"] != "Menunggu" else ""), reverse=False)
    return rows

@api.get("/reservations/mine")
async def my_reservations(user=Depends(current_user)):
    member = await db.members.find_one(own_member_filter(user), {"_id":0})
    if not member: return []
    return await db.reservations.find({"member_id": member["id"]}, {"_id":0}).sort("created_at", -1).to_list(100)

@api.post("/reservations")
async def reserve(data: ReservationInput, user=Depends(current_user)):
    member = await db.members.find_one(own_member_filter(user), {"_id":0})
    if not member: raise HTTPException(404, "Data keanggotaan belum terdaftar. Hubungi petugas perpustakaan.")
    book = await db.books.find_one({"id": data.book_id}, {"_id":0})
    if not book: raise HTTPException(404, "Buku tidak ditemukan")
    if book["status"] == "Hilang": raise HTTPException(400, "Buku sedang hilang, tidak bisa dipesan")
    if await db.reservations.find_one({"book_id": book["id"], "member_id": member["id"], "status": "Menunggu"}):
        raise HTTPException(400, "Kamu sudah memesan buku ini")
    if await db.reservations.count_documents({"member_id": member["id"], "status": "Menunggu"}) >= 3:
        raise HTTPException(400, "Maksimal 3 pesanan aktif")
    doc = {"id":"RS-"+str(uuid.uuid4())[:8].upper(),"book_id":book["id"],"book_title":book["title"],"book_shelf":book["shelf"],"member_id":member["id"],"member_name":member["name"],"class_name":member["class_name"],"status":"Menunggu","created_at":now_iso(),"processed_at":None,"processed_by":None}
    await db.reservations.insert_one(doc); return public(doc)

@api.delete("/reservations/{res_id}")
async def cancel_reservation(res_id: str, user=Depends(current_user)):
    res = await db.reservations.find_one({"id": res_id}, {"_id":0})
    if not res: raise HTTPException(404, "Pesanan tidak ditemukan")
    if user["role"] == "siswa":
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
        if not book or book["status"] != "Tersedia": raise HTTPException(400, "Buku belum tersedia untuk dipinjamkan")
        await db.books.update_one({"id": book["id"]}, {"$set": {"status":"Dipinjam"}})
        await db.transactions.insert_one({"id":"TRX-"+str(uuid.uuid4())[:8].upper(),"member_id":res["member_id"],"member_name":res["member_name"],"book_id":book["id"],"book_title":book["title"],"action":"pinjam","date":now_iso(),"reservation_id":res_id})
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
    return {**DEFAULT_SETTINGS, **(doc or {})}

@api.put("/settings")
async def put_settings(data: SettingsInput, user=Depends(current_user)):
    staff_only(user)
    await db.settings.update_one({"id":"main"}, {"$set": data.model_dump()}, upsert=True)
    return data.model_dump()

@api.get("/books")
async def books(user=Depends(current_user)):
    rows = await db.books.find({}, {"_id":0}).sort("created_at", -1).to_list(500)
    waiting = {r["_id"]: r["n"] for r in await db.reservations.aggregate([{"$match":{"status":"Menunggu"}},{"$group":{"_id":"$book_id","n":{"$sum":1}}}]).to_list(500)}
    for b in rows: b["waiting"] = waiting.get(b["id"], 0)
    return rows

@api.post("/books")
async def add_book(data: BookInput, user=Depends(current_user)):
    if user["role"] == "siswa": raise HTTPException(403,"Siswa tidak dapat menambah buku")
    doc = data.model_dump(); doc.update({"id":"BK-"+str(uuid.uuid4())[:8].upper(),"created_at":now_iso()}); await db.books.insert_one(doc); return public(doc)

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
    if data.status == "Hilang" and book["status"] == "Hilang": raise HTTPException(400, "Buku sudah berstatus hilang")
    await db.books.update_one({"id":book_id}, {"$set":{"status":data.status}})
    if data.status == "Hilang":
        report = {"id":"LS-"+str(uuid.uuid4())[:8].upper(),"book_id":book_id,"title":book["title"],"code":book_id,"detail":data.note or book_id,"date":now_iso(),"status":"Hilang","reported_by":data.reporter.strip() or user["name"]}
        await db.missing.insert_one(report); return public(report)
    await db.missing.update_many({"book_id":book_id,"status":"Hilang"}, {"$set":{"status":"Ditemukan","found_at":now_iso()}})
    return {"ok":True, "status":"Tersedia"}

@api.get("/incoming")
async def incoming_list(user=Depends(current_user)):
    staff_only(user)
    return await db.incoming.find({}, {"_id":0}).sort("date",-1).to_list(200)

@api.post("/incoming")
async def add_incoming(data: IncomingInput, user=Depends(current_user)):
    staff_only(user)
    date = data.date or now_iso()[:10]
    base = data.model_dump(exclude={"quantity","date","source"})
    books = [{**base, "id":"BK-"+str(uuid.uuid4())[:8].upper(), "status":"Tersedia", "created_at":now_iso()} for _ in range(data.quantity)]
    await db.books.insert_many(books)
    doc = {"id":"IN-"+str(uuid.uuid4())[:8].upper(),"title":data.title,"author":data.author,"category":data.category,"shelf":data.shelf,"quantity":data.quantity,"detail":f"{data.quantity} eksemplar","source":data.source,"date":date,"status":"Tersimpan","book_ids":[b["id"] for b in books],"recorded_by":user["name"],"created_at":now_iso()}
    await db.incoming.insert_one(doc); return public(doc)

@api.get("/members")
async def members(user=Depends(current_user)):
    staff_only(user)
    return await db.members.find({}, {"_id":0}).to_list(200)

@api.post("/members")
async def add_member(data: MemberInput, user=Depends(current_user)):
    if user["role"] == "siswa": raise HTTPException(403,"Siswa tidak dapat menambah anggota")
    doc=data.model_dump(); doc.update({"id":"MB-"+str(uuid.uuid4())[:8].upper()}); await db.members.insert_one(doc); return public(doc)

@api.put("/members/{member_id}")
async def update_member(member_id: str, data: MemberInput, user=Depends(current_user)):
    staff_only(user)
    member = await db.members.find_one({"id": member_id}, {"_id":0})
    if not member: raise HTTPException(404, "Anggota tidak ditemukan")
    await db.members.update_one({"id": member_id}, {"$set": data.model_dump()})
    updated = await db.members.find_one({"id": member_id}, {"_id":0})
    return updated

@api.post("/members/bulk-delete")
async def bulk_delete_members(data: BulkDeleteInput, user=Depends(current_user)):
    staff_only(user)
    members = await db.members.find({"class_name": data.class_name}, {"_id":0,"id":1}).to_list(1000)
    ids = [m["id"] for m in members]
    if not ids: raise HTTPException(404, "Tidak ada anggota pada kelas tersebut")
    await db.reservations.update_many({"member_id": {"$in": ids}, "status": "Menunggu"}, {"$set": {"status":"Dibatalkan","processed_at":now_iso(),"processed_by":user["name"]}})
    result = await db.members.delete_many({"id": {"$in": ids}})
    return {"ok": True, "deleted": result.deleted_count, "class_name": data.class_name}

@api.delete("/members/{member_id}")
async def delete_member(member_id: str, user=Depends(current_user)):
    staff_only(user)
    result = await db.members.delete_one({"id": member_id})
    if result.deleted_count == 0: raise HTTPException(404, "Anggota tidak ditemukan")
    await db.reservations.update_many({"member_id": member_id, "status": "Menunggu"}, {"$set": {"status":"Dibatalkan","processed_at":now_iso(),"processed_by":user["name"]}})
    return {"ok": True}

@api.post("/admin/reset-data")
async def reset_data(data: ResetInput, user=Depends(current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Hanya admin yang dapat mereset data")
    members = (await db.members.delete_many({})).deleted_count
    transactions = (await db.transactions.delete_many({})).deleted_count
    incoming = (await db.incoming.delete_many({})).deleted_count
    missing = (await db.missing.delete_many({})).deleted_count
    reservations = (await db.reservations.delete_many({})).deleted_count
    stocktake = (await db.stocktake.delete_many({})).deleted_count
    if data.include_books:
        books = (await db.books.delete_many({})).deleted_count
    else:
        books = 0
        await db.books.update_many({}, {"$set": {"status": "Tersedia"}})
    await db.meta.update_one({"id": "seed"}, {"$set": {"id": "seed", "done": True}}, upsert=True)
    return {"ok": True, "deleted": {"members": members, "transactions": transactions, "incoming": incoming, "missing": missing, "reservations": reservations, "stocktake": stocktake, "books": books}, "books_deleted": data.include_books}

@api.get("/members/{member_id}/history")
async def member_history(member_id: str, user=Depends(current_user)):
    staff_only(user)
    member = await db.members.find_one({"id":member_id}, {"_id":0})
    if not member: raise HTTPException(404, "Anggota tidak ditemukan")
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
async def shelves(user=Depends(current_user)): return await db.shelves.find({}, {"_id":0}).to_list(50)

@api.get("/transactions")
async def transactions(user=Depends(current_user)):
    staff_only(user)
    return await db.transactions.find({}, {"_id":0}).sort("date",-1).to_list(200)

@api.post("/transactions")
async def transaction(data: TransactionInput, user=Depends(current_user)):
    staff_only(user)
    member=await db.members.find_one({"id":data.member_id},{"_id":0}); book=await db.books.find_one({"id":data.book_id},{"_id":0})
    if not member or not book: raise HTTPException(404,"Anggota atau buku tidak ditemukan")
    action=data.action; status="Dipinjam" if action=="pinjam" else "Tersedia"
    if action=="pinjam" and book["status"] != "Tersedia": raise HTTPException(400,"Buku sedang dipinjam")
    await db.books.update_one({"id":book["id"]},{"$set":{"status":status}})
    doc={"id":"TRX-"+str(uuid.uuid4())[:8].upper(),"member_id":member["id"],"member_name":member["name"],"book_id":book["id"],"book_title":book["title"],"action":action,"date":now_iso()}; await db.transactions.insert_one(doc); return public(doc)

@api.get("/reports")
async def reports(user=Depends(current_user)):
    staff_only(user)
    tx=await db.transactions.find({}, {"_id":0}).sort("date",-1).to_list(500)
    incoming=await db.incoming.find({}, {"_id":0}).sort("date",-1).to_list(200)
    missing=await db.missing.find({}, {"_id":0}).sort("date",-1).to_list(200)
    return {"transactions":tx,"loans":build_loans(tx),"incoming":incoming,"missing":missing}

async def export_rows(type: str, period: str):
    if type not in ("transaksi","masuk","hilang"): raise HTTPException(400, "Jenis laporan tidak valid")
    now = datetime.now(WIB)
    if type == "transaksi":
        rows = build_loans(await db.transactions.find({}, {"_id":0}).to_list(2000))
    elif type == "masuk":
        rows = await db.incoming.find({}, {"_id":0}).sort("date",-1).to_list(2000)
    else:
        rows = await db.missing.find({}, {"_id":0}).sort("date",-1).to_list(2000)
    rows = [r for r in rows if in_period(r.get("date"), period, now)]
    settings = await db.settings.find_one({"id":"main"}, {"_id":0}) or {}
    return rows, settings, now

@api.get("/reports/export.pdf")
async def export_report(type: str = "transaksi", period: str = "semua", user=Depends(current_user)):
    staff_only(user)
    rows, settings, now = await export_rows(type, period)
    pdf = render_report_pdf(type, period, rows, settings, user["name"])
    filename = f"laporan-{type}-{period}-{now.strftime('%Y%m%d')}.pdf"
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@api.get("/reports/export.xlsx")
async def export_report_xlsx(type: str = "transaksi", period: str = "semua", user=Depends(current_user)):
    staff_only(user)
    rows, settings, now = await export_rows(type, period)
    data = render_report_xlsx(type, period, rows, settings, user["name"])
    filename = f"laporan-{type}-{period}-{now.strftime('%Y%m%d')}.xlsx"
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=[os.environ["FRONTEND_URL"]], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown(): client.close()