from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, uuid, bcrypt, jwt

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

class BookInput(BaseModel):
    title: str
    author: str
    category: str = "Umum"
    shelf: str = "R-01"
    isbn: str = ""
    status: str = "Tersedia"

class MemberInput(BaseModel):
    name: str
    student_id: str
    class_name: str
    email: str = ""
    phone: str = ""
    photo: str = ""

class TransactionInput(BaseModel):
    member_id: str
    book_id: str
    action: str = "pinjam"

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
            {"id":"u-siswa","name":"Bima Pratama","email":"siswa@smansa.sch.id","role":"siswa","password_hash":password_hash("siswa123")},
        ]
        await db.users.insert_many(users)
    if await db.shelves.count_documents({}) == 0:
        await db.shelves.insert_many([{ "id":"R-01", "name":"Pengetahuan Umum", "color":"azure", "capacity":80 }, {"id":"R-02","name":"Sains & Teknologi","color":"mint","capacity":60},{"id":"R-03","name":"Bahasa & Sastra","color":"amber","capacity":50}])
    if await db.books.count_documents({}) == 0:
        await db.books.insert_many([
            {"id":"BK-1042","title":"Laskar Pelangi","author":"Andrea Hirata","category":"Sastra","shelf":"R-03","isbn":"9789793062792","status":"Tersedia","created_at":now_iso()},
            {"id":"BK-1043","title":"Ensiklopedia Sains Remaja","author":"Tim Edukasi","category":"Sains","shelf":"R-02","isbn":"9786021234567","status":"Dipinjam","created_at":now_iso()},
            {"id":"BK-1044","title":"Matematika Dasar SMA","author":"D. Kurniawan","category":"Pelajaran","shelf":"R-01","isbn":"9786027654321","status":"Tersedia","created_at":now_iso()},
            {"id":"BK-1045","title":"Bumi Manusia","author":"Pramoedya Ananta Toer","category":"Sastra","shelf":"R-03","isbn":"9789799731234","status":"Tersedia","created_at":now_iso()},
        ])
    if await db.members.count_documents({}) == 0:
        await db.members.insert_many([{"id":"MB-2024001","name":"Bima Pratama","student_id":"24001","class_name":"XI IPA 2","email":"bima@siswa.sch.id","phone":"081234567890","photo":""},{"id":"MB-2024002","name":"Siti Rahma","student_id":"24002","class_name":"X IPS 1","email":"siti@siswa.sch.id","phone":"081298765432","photo":""},{"id":"MB-2024003","name":"Raka Wijaya","student_id":"24003","class_name":"XII IPA 1","email":"raka@siswa.sch.id","phone":"081277766655","photo":""}])
    if await db.transactions.count_documents({}) == 0:
        await db.transactions.insert_many([{ "id":"TRX-001","member_id":"MB-2024001","member_name":"Bima Pratama","book_id":"BK-1043","book_title":"Ensiklopedia Sains Remaja","action":"pinjam","date":now_iso()},{"id":"TRX-002","member_id":"MB-2024002","member_name":"Siti Rahma","book_id":"BK-1042","book_title":"Laskar Pelangi","action":"kembali","date":now_iso()}])

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
    response.set_cookie("access_token", token_for(user), httponly=True, samesite="lax", max_age=28800)
    return public(user)

@api.get("/auth/me")
async def me(user=Depends(current_user)): return public(user)

@api.post("/auth/logout")
async def logout(response: Response): response.delete_cookie("access_token"); return {"ok":True}

@api.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    return {"books":await db.books.count_documents({}),"members":await db.members.count_documents({}),"borrowed":await db.books.count_documents({"status":"Dipinjam"}),"missing":await db.books.count_documents({"status":"Hilang"}),"incoming":4,"transactions":await db.transactions.count_documents({})}

@api.get("/books")
async def books(user=Depends(current_user)): return await db.books.find({}, {"_id":0}).sort("created_at", -1).to_list(200)

@api.post("/books")
async def add_book(data: BookInput, user=Depends(current_user)):
    if user["role"] == "siswa": raise HTTPException(403,"Siswa tidak dapat menambah buku")
    doc = data.model_dump(); doc.update({"id":"BK-"+str(uuid.uuid4())[:8].upper(),"created_at":now_iso()}); await db.books.insert_one(doc); return public(doc)

@api.delete("/books/{book_id}")
async def delete_book(book_id: str, user=Depends(current_user)):
    if user["role"] not in ["admin","petugas"]: raise HTTPException(403,"Akses ditolak")
    result = await db.books.delete_one({"id":book_id})
    if result.deleted_count == 0: raise HTTPException(404, "Buku tidak ditemukan")
    return {"ok":True}

@api.get("/members")
async def members(user=Depends(current_user)): return await db.members.find({}, {"_id":0}).to_list(200)

@api.post("/members")
async def add_member(data: MemberInput, user=Depends(current_user)):
    if user["role"] == "siswa": raise HTTPException(403,"Siswa tidak dapat menambah anggota")
    doc=data.model_dump(); doc.update({"id":"MB-"+str(uuid.uuid4())[:8].upper()}); await db.members.insert_one(doc); return public(doc)

@api.get("/shelves")
async def shelves(user=Depends(current_user)): return await db.shelves.find({}, {"_id":0}).to_list(50)

@api.get("/transactions")
async def transactions(user=Depends(current_user)): return await db.transactions.find({}, {"_id":0}).sort("date",-1).to_list(200)

@api.post("/transactions")
async def transaction(data: TransactionInput, user=Depends(current_user)):
    member=await db.members.find_one({"id":data.member_id},{"_id":0}); book=await db.books.find_one({"id":data.book_id},{"_id":0})
    if not member or not book: raise HTTPException(404,"Anggota atau buku tidak ditemukan")
    action=data.action; status="Dipinjam" if action=="pinjam" else "Tersedia"
    if action=="pinjam" and book["status"] != "Tersedia": raise HTTPException(400,"Buku sedang dipinjam")
    await db.books.update_one({"id":book["id"]},{"$set":{"status":status}})
    doc={"id":"TRX-"+str(uuid.uuid4())[:8].upper(),"member_id":member["id"],"member_name":member["name"],"book_id":book["id"],"book_title":book["title"],"action":action,"date":now_iso()}; await db.transactions.insert_one(doc); return public(doc)

@api.get("/reports")
async def reports(user=Depends(current_user)):
    tx=await db.transactions.find({}, {"_id":0}).sort("date",-1).to_list(200)
    return {"transactions":tx,"incoming":[{"title":"Modul Literasi Digital","quantity":12,"detail":"12 eksemplar","date":"18 Jun 2024","status":"Tersimpan"},{"title":"Koleksi Sains Terapan","quantity":8,"detail":"8 eksemplar","date":"15 Jun 2024","status":"Tersimpan"}],"missing":[{"title":"Kamus Bahasa Inggris","code":"BK-0988","detail":"BK-0988","date":"03 Jun 2024","status":"Ditindaklanjuti"}]}

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=[os.environ["FRONTEND_URL"]], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown(): client.close()