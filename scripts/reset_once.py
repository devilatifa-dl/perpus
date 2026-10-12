import requests

BASE = "http://localhost:8001/api"
s = requests.Session()

# login as admin
r = s.post(f"{BASE}/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"})
print("login:", r.status_code, r.json().get("name") if r.ok else r.text)
r.raise_for_status()

# reset data including books
r = s.post(f"{BASE}/admin/reset-data", json={"include_books": True})
print("reset:", r.status_code, r.json() if r.ok else r.text)
r.raise_for_status()

# verify counts
for ep in ["books", "members", "transactions"]:
    rr = s.get(f"{BASE}/{ep}")
    print(ep, "count:", len(rr.json()) if rr.ok else rr.text)
