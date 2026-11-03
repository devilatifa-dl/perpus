import io, os, sys, time, zipfile, requests

BASE = os.environ.get("BASE", "https://perpus-devilatifa--369vmy1r.preview.emergentagent.com") + "/api"
s = requests.Session()
t = s.post(f"{BASE}/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}).json()["token"]
H = {"Authorization": f"Bearer {t}"}

r = s.get(f"{BASE}/admin/backup.zip", headers=H)
print("download", r.status_code, r.headers.get("content-type"), r.headers.get("content-encoding"), len(r.content))
data = r.content
try:
    z = zipfile.ZipFile(io.BytesIO(data)); print("zip ok, members:", len(z.namelist()), z.testzip())
except Exception as e:
    print("ZIP BROKEN", e); sys.exit(1)


def restore(blob, name):
    CH = 8 * 1024 * 1024
    n = max(1, -(-len(blob) // CH))
    st = s.post(f"{BASE}/admin/restore/start", json={"filename": name, "size": len(blob), "chunks": n}, headers=H)
    print("start", st.status_code, st.text[:200]); st = st.json()
    for i in range(n):
        part = blob[i * CH:(i + 1) * CH]
        rr = s.put(f"{BASE}/admin/restore/chunk", params={"upload_id": st["upload_id"], "index": i}, data=part, headers={**H, "Content-Type": "application/octet-stream"})
        print(" chunk", i, len(part), rr.status_code, rr.text[:120])
    f = s.post(f"{BASE}/admin/restore/finish", json={"upload_id": st["upload_id"]}, headers=H)
    print("finish", f.status_code, f.text[:200])
    for _ in range(60):
        time.sleep(2)
        j = s.get(f"{BASE}/admin/restore/status/{st['upload_id']}", headers=H).json()
        if j["status"] in ("done", "error"):
            print("RESULT", name, j); return j
    print("timeout")


mode = sys.argv[1] if len(sys.argv) > 1 else "small"
if mode in ("small", "all"):
    restore(data, "backup.zip")
if mode in ("big", "all"):
    # zip > 8MB (beberapa potongan): tambahkan berkas acak tak terkompresi
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for n in src.namelist():
            dst.writestr(n, src.read(n))
        dst.writestr("laporan/pad.bin", os.urandom(19 * 1024 * 1024), compress_type=zipfile.ZIP_STORED)
    restore(buf.getvalue(), "big.zip")
