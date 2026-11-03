"""Simulasi: ZIP cadangan terpotong di 9 MiB (seperti berkas pengguna) -> harus tetap bisa dipulihkan.
Juga cek ZIP cadangan berisi laporan Peringkat Rajin Meminjam."""
import io, json, os, sys, time, zipfile, requests
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("BASE", "https://perpus-devilatifa--369vmy1r.preview.emergentagent.com") + "/api"
s = requests.Session()
t = s.post(f"{BASE}/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}).json()["token"]
H = {"Authorization": f"Bearer {t}"}
CH = 8 * 1024 * 1024


def restore(blob, name):
    n = max(1, -(-len(blob) // CH))
    st = s.post(f"{BASE}/admin/restore/start", json={"filename": name, "size": len(blob), "chunks": n}, headers=H).json()
    for i in range(n):
        r = s.put(f"{BASE}/admin/restore/chunk", params={"upload_id": st["upload_id"], "index": i}, data=blob[i * CH:(i + 1) * CH], headers={**H, "Content-Type": "application/octet-stream"})
        assert r.status_code == 200, r.text
    assert s.post(f"{BASE}/admin/restore/finish", json={"upload_id": st["upload_id"]}, headers=H).status_code == 200
    for _ in range(90):
        time.sleep(2)
        j = s.get(f"{BASE}/admin/restore/status/{st['upload_id']}", headers=H).json()
        if j["status"] in ("done", "error"):
            return j
    return {"status": "timeout"}


now = datetime.now(timezone.utc)
books = [{"id": f"BK-9{i:03d}", "title": f"Buku Uji {i}", "author": "Penulis", "category": "Umum", "shelf": "R-01", "stock": 2, "available": 2, "borrowed": 0, "lost": 0, "status": "Tersedia", "cover": ""} for i in range(5)]
members = [{"id": f"MB-9{i:03d}", "name": f"Siswa Uji {i}", "class_name": "X IPA 1" if i % 2 else "XI IPS 2", "student_id": f"99{i:03d}", "type": "Siswa", "status": "Aktif", "photo": ""} for i in range(4)]
tx = []
for i in range(8):
    d = (now - timedelta(days=i % 3)).isoformat()
    m = members[i % 4]; b = books[i % 5]
    tx.append({"id": f"TRX-T{i}P", "member_id": m["id"], "member_name": m["name"], "class_name": m["class_name"], "book_id": b["id"], "book_title": b["title"], "action": "pinjam", "date": d})
    tx.append({"id": f"TRX-T{i}K", "member_id": m["id"], "member_name": m["name"], "class_name": m["class_name"], "book_id": b["id"], "book_title": b["title"], "action": "kembali", "date": d})
payload = {"app": "perpustakaan-sma1-abung-tengah", "version": 1, "generated_at": now.isoformat(), "collections": {
    "books": books, "members": members, "transactions": tx, "incoming": [], "missing": [], "reservations": [], "stocktake": [],
    "shelves": [{"id": "R-01", "name": "Pengetahuan Umum", "capacity": 100}], "settings": [], "visits": []}}

# ZIP mirip buatan server: data-cadangan.json di awal, lalu laporan besar
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("data-cadangan.json", json.dumps(payload, ensure_ascii=False, indent=2))
    for k in range(3):
        z.writestr(f"laporan/0{k}-Laporan.pdf", os.urandom(4 * 1024 * 1024), compress_type=zipfile.ZIP_STORED)
    z.writestr("BACA-SAYA.txt", "x")
full = buf.getvalue()
cut = full[:9435136]  # tepat 9 MiB seperti berkas pengguna
try:
    zipfile.ZipFile(io.BytesIO(cut)); print("unexpected: truncated zip opened")
except zipfile.BadZipFile as e:
    print("truncated zip is BadZipFile as expected:", e)

res = restore(cut, "backup-terpotong.zip")
print("TRUNCATED RESTORE:", res)
ok1 = res.get("status") == "done" and res.get("salvaged") is True and res["restored"]["transactions"] == 16 and res["restored"]["books"] == 5

# ZIP yang JSON-nya sendiri terpotong -> pesan jelas
bad = full[:200]
res2 = restore(bad, "rusak-total.zip")
print("BROKEN JSON RESTORE:", res2.get("status"), res2.get("error"))
ok2 = res2.get("status") == "error" and "terpotong" in (res2.get("error") or "")

# Unduh cadangan ZIP -> utuh, ada header ukuran, ada laporan peringkat rajin meminjam
r = s.get(f"{BASE}/admin/backup.zip", headers=H)
names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
loan = [n for n in names if "06-Peringkat-Rajin-Meminjam" in n]
print("download", len(r.content), "X-Backup-Bytes", r.headers.get("x-backup-bytes"), "loan reports:", loan)
ok3 = r.headers.get("x-backup-bytes") == str(len(r.content)) and any(n.endswith(".pdf") for n in loan) and any(n.endswith(".xlsx") for n in loan)

# ZIP utuh normal masih bisa dipulihkan & tidak ditandai salvaged
res4 = restore(r.content, "backup-utuh.zip")
print("FULL RESTORE:", res4.get("status"), res4.get("salvaged"), res4.get("restored"))
ok4 = res4.get("status") == "done" and not res4.get("salvaged") and res4["restored"]["transactions"] == 16

print("RESULT", ok1, ok2, ok3, ok4)
sys.exit(0 if all([ok1, ok2, ok3, ok4]) else 1)
