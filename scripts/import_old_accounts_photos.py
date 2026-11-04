"""Masukkan foto & akun dari server lama ke database preview. Kredensial dibaca dari .env, tidak dicetak."""
import os, json, uuid, bcrypt
from datetime import datetime, timezone
from dotenv import dotenv_values
from pymongo import MongoClient
from PIL import Image

env = dotenv_values("/app/backend/.env")
db = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]
OUT = "/tmp/oldsrv"

# 1. Foto anggota
n = 0
for fn in os.listdir(f"{OUT}/files"):
    path = fn.replace("__", "/")
    raw = open(f"{OUT}/files/{fn}", "rb").read()
    w, h = Image.open(f"{OUT}/files/{fn}").size
    db.files.update_one({"storage_path": path}, {"$set": {"storage_path": path, "data": raw, "content_type": "image/jpeg", "size": len(raw), "width": w, "height": h, "is_deleted": False, "original_filename": fn, "original_size": len(raw), "uploaded_by": "restore-old-server"}, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    n += 1
print("photos inserted", n)

# 2. Akun staf: samakan nama/email/peran dengan server lama
old_users = json.load(open(f"{OUT}/users.json"))
admin_email = env["OLD_SERVER_ADMIN_EMAIL"].strip().lower()
for u in old_users:
    upd = {"name": u["name"], "email": u["email"], "role": u["role"]}
    if u["email"].lower() == admin_email:
        upd["password_hash"] = bcrypt.hashpw(env["OLD_SERVER_ADMIN_PASSWORD"].encode(), bcrypt.gensalt()).decode()
    existing = db.users.find_one({"id": u["id"]}) or db.users.find_one({"email": u["email"]})
    if existing:
        db.users.update_one({"_id": existing["_id"]}, {"$set": upd})
        print("updated", u["id"], u["role"], "(password synced)" if "password_hash" in upd else "(password kept)")
    else:
        if "password_hash" not in upd:
            print("skip new user without password", u["id"]); continue
        db.users.insert_one({"id": u["id"], **upd})
        print("inserted", u["id"])

# 3. Akun login per siswa (jika ada)
accs = json.load(open(f"{OUT}/member_accounts.json"))
print("member accounts to copy", len(accs))
print("users now:", [(x["id"], x["role"]) for x in db.users.find({}, {"id": 1, "role": 1})])
