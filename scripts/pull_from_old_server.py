"""Ambil data dari server lama (hanya baca) ke /tmp/oldsrv. Kredensial dari backend/.env, tidak dicetak."""
import os, sys, json, requests
from dotenv import dotenv_values

env = dotenv_values("/app/backend/.env")
BASE = "https://library-devilatifa.emergent.host/api"
OUT = "/tmp/oldsrv"
os.makedirs(OUT, exist_ok=True)

s = requests.Session()
r = s.post(f"{BASE}/auth/login", json={"email": env["OLD_SERVER_ADMIN_EMAIL"].strip(), "password": env["OLD_SERVER_ADMIN_PASSWORD"], "portal": "admin"}, timeout=60)
print("login", r.status_code, r.text[:200] if r.status_code != 200 else "")
if r.status_code != 200:
    sys.exit(1)
me = r.json()
print("as", me.get("name"), me.get("role"))
s.headers["Authorization"] = f"Bearer {me['token']}"

step = sys.argv[1] if len(sys.argv) > 1 else "info"
if step in ("info", "all"):
    u = s.get(f"{BASE}/users", timeout=60)
    print("users", u.status_code, len(u.json()) if u.ok else u.text[:200])
    if u.ok:
        json.dump(u.json(), open(f"{OUT}/users.json", "w"), ensure_ascii=False)
if step in ("backup", "all"):
    b = s.get(f"{BASE}/admin/backup", timeout=600)
    print("backup", b.status_code, len(b.content))
    if b.ok:
        open(f"{OUT}/backup.json", "wb").write(b.content)
        data = b.json()["collections"]
        print({k: len(v) for k, v in data.items()})
if step in ("accounts", "all"):
    from concurrent.futures import ThreadPoolExecutor
    data = json.load(open(f"{OUT}/backup.json"))["collections"]
    def acc(m):
        a = s.get(f"{BASE}/members/{m['id']}/account", timeout=60)
        return m["id"], a.status_code, (a.json() if a.ok else None)
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(acc, data["members"]))
    bad = [r for r in res if r[1] != 200]
    accounts = [r[2] for r in res if r[2]]
    json.dump(accounts, open(f"{OUT}/member_accounts.json", "w"), ensure_ascii=False)
    print("member accounts", len(accounts), "errors", len(bad))
if step in ("photos", "all"):
    data = json.load(open(f"{OUT}/backup.json"))["collections"]
    os.makedirs(f"{OUT}/files", exist_ok=True)
    urls = set()
    for m in data.get("members", []):
        p = m.get("photo") or ""
        if p.startswith("/api/files/"):
            urls.add(p)
    for st in data.get("settings", []):
        for k, v in st.items():
            if isinstance(v, str) and v.startswith("/api/files/"):
                urls.add(v)
    ok = fail = 0
    for p in sorted(urls):
        path = p[len("/api/files/"):]
        dest = os.path.join(f"{OUT}/files", path.replace("/", "__"))
        if os.path.exists(dest):
            ok += 1; continue
        try:
            f = s.get(f"{BASE}/files/{path}", timeout=60)
            if f.ok and f.content:
                open(dest, "wb").write(f.content); ok += 1
            else:
                fail += 1; print("fail", f.status_code, path)
        except Exception as e:
            fail += 1; print("err", path, e)
    print("photos total", len(urls), "ok", ok, "fail", fail)
