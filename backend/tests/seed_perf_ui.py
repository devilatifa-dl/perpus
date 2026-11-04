# Seed / cleanup helper for lazy-list UI testing. Usage: python seed_perf_ui.py seed|cleanup
import json, os, sys, requests
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
IDS = "/tmp/perf_seed_ids.json"
DB = MongoClient("mongodb://localhost:27017")["test_database"]


def sess():
    s = requests.Session()
    t = s.post(f"{BASE}/api/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}).json()["token"]
    s.headers["Authorization"] = f"Bearer {t}"
    return s


def seed():
    s = sess(); ids = {"books": [], "members": [], "visits": [], "tx": []}
    for i in range(120):
        r = s.post(f"{BASE}/api/books", json={"title": f"TEST_Perf Buku {i:03d}", "author": "TEST_Penulis", "stock": 1, "category": "Umum", "shelf": "R-01"})
        ids["books"].append(r.json()["id"])
    for i in range(60):
        r = s.post(f"{BASE}/api/members", json={"name": f"TEST_Siswa {i:03d}", "student_id": f"TESTNIS{i:03d}", "class_name": "TEST_KELAS"})
        ids["members"].append(r.json()["id"])
    for i in range(60):
        r = s.post(f"{BASE}/api/visits/guest", json={"name": f"TEST_Tamu {i:03d}", "origin": "TEST", "purpose": "Membaca"})
        if r.status_code == 200: ids["visits"].append(r.json()["id"])
    for i in range(60):
        r = s.post(f"{BASE}/api/transactions", json={"member_id": ids["members"][i], "book_id": ids["books"][i], "action": "pinjam"})
        if r.status_code == 200: ids["tx"].append(r.json()["id"])
    json.dump(ids, open(IDS, "w"))
    print({k: len(v) for k, v in ids.items()})


def cleanup():
    s = sess(); ids = json.load(open(IDS))
    for v in ids["visits"]: s.delete(f"{BASE}/api/visits/{v}")
    DB.transactions.delete_many({"id": {"$in": ids["tx"]}})
    for b in ids["books"]: s.delete(f"{BASE}/api/books/{b}")
    for m in ids["members"]: s.delete(f"{BASE}/api/members/{m}")
    DB.visits.delete_many({"id": {"$in": ids["visits"]}})
    print("left:", DB.books.count_documents({"id": {"$in": ids["books"]}}), DB.members.count_documents({"id": {"$in": ids["members"]}}), DB.visits.count_documents({"id": {"$in": ids["visits"]}}), DB.transactions.count_documents({"id": {"$in": ids["tx"]}}))


if __name__ == "__main__":
    {"seed": seed, "cleanup": cleanup}[sys.argv[1]]()
