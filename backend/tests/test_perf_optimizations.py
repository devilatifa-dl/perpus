# Performance optimizations: server-side cover compression, photo upload compression, DB indexes, service worker
import base64, io, os, uuid
import pytest, requests
from PIL import Image
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
DB = MongoClient("mongodb://localhost:27017")["test_database"]


def _png_data_url(w, h, noisy=True):
    img = Image.new("RGB", (w, h))
    if noisy:
        # gradient + random noise block so the PNG is genuinely large
        img = Image.effect_noise((w, h), 60).convert("RGB")
        grad = Image.linear_gradient("L").resize((w, h)).convert("RGB")
        img = Image.blend(img, grad, 0.5)
    else:
        img.paste((200, 30, 30), (0, 0, w, h))
    buf = io.BytesIO(); img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), len(buf.getvalue())


def _decode(data_url):
    raw = base64.b64decode(data_url.split(",", 1)[1])
    im = Image.open(io.BytesIO(raw))
    return raw, im


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"})
    if r.status_code != 200:
        pytest.skip("admin login failed")
    ses.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return ses


@pytest.fixture(scope="module")
def created(s):
    ids = []
    yield ids
    for bid in ids:
        s.delete(f"{BASE_URL}/api/books/{bid}")


# Cover compression on POST /api/books
class TestCoverCompression:
    def test_large_cover_compressed_on_create(self, s, created):
        url, size = _png_data_url(3000, 4000)
        assert size > 400 * 1024
        r = s.post(f"{BASE_URL}/api/books", json={"title": f"TEST_BigCover_{uuid.uuid4().hex[:6]}", "author": "TEST_A", "stock": 1, "category": "Umum", "shelf": "R-01", "cover": url}, timeout=120)
        assert r.status_code == 200, r.text
        bid = r.json()["id"]; created.append(bid)
        doc = DB.books.find_one({"id": bid})
        assert doc["cover"].startswith("data:image/jpeg;base64,")
        raw, im = _decode(doc["cover"])
        print("stored bytes", len(raw), im.size)
        assert im.format == "JPEG"
        assert max(im.size) <= 1000
        assert len(raw) <= 400 * 1024
        # slim list returns ref URL, cover endpoint serves image
        lst = s.get(f"{BASE_URL}/api/books").json()
        b = next(x for x in lst if x["id"] == bid)
        assert b["cover"].startswith("/api/books/")
        c = requests.get(f"{BASE_URL}{b['cover']}")
        assert c.status_code == 200 and c.headers["content-type"].startswith("image/")

    def test_small_cover_untouched(self, s, created):
        url, _ = _png_data_url(200, 300, noisy=False)
        r = s.post(f"{BASE_URL}/api/books", json={"title": f"TEST_SmallCover_{uuid.uuid4().hex[:6]}", "author": "TEST_A", "stock": 1, "cover": url})
        assert r.status_code == 200
        bid = r.json()["id"]; created.append(bid)
        assert DB.books.find_one({"id": bid})["cover"] == url

    def test_put_compresses_and_ref_keeps_cover(self, s, created):
        r = s.post(f"{BASE_URL}/api/books", json={"title": f"TEST_PutCover_{uuid.uuid4().hex[:6]}", "author": "TEST_A", "stock": 1})
        bid = r.json()["id"]; created.append(bid)
        url, _ = _png_data_url(2500, 3500)
        r = s.put(f"{BASE_URL}/api/books/{bid}", json={"title": r.json()["title"], "author": "TEST_A", "category": "Umum", "shelf": "R-01", "isbn": "", "cover": url}, timeout=120)
        assert r.status_code == 200, r.text
        doc = DB.books.find_one({"id": bid})
        raw, im = _decode(doc["cover"])
        assert im.format == "JPEG" and max(im.size) <= 1000 and len(raw) <= 400 * 1024
        before = doc["cover"]
        # edit again with the ref URL -> cover must remain unchanged
        ref = r.json()["cover"]
        assert ref.startswith("/api/books/")
        r2 = s.put(f"{BASE_URL}/api/books/{bid}", json={"title": doc["title"], "author": "TEST_A", "category": "Sains", "shelf": "R-01", "isbn": "", "cover": ref})
        assert r2.status_code == 200
        after = DB.books.find_one({"id": bid})
        assert after["cover"] == before and after["category"] == "Sains"

    def test_incoming_compresses(self, s, created):
        url, _ = _png_data_url(3000, 3000)
        title = f"TEST_Incoming_{uuid.uuid4().hex[:6]}"
        r = s.post(f"{BASE_URL}/api/incoming", json={"title": title, "author": "TEST_A", "quantity": 1, "source": "TEST", "category": "Umum", "shelf": "R-01", "cover": url}, timeout=120)
        if r.status_code == 422:
            pytest.skip(f"incoming payload mismatch: {r.text[:200]}")
        assert r.status_code == 200, r.text
        doc = DB.books.find_one({"title": title})
        assert doc
        created.append(doc["id"])
        raw, im = _decode(doc["cover"])
        assert im.format == "JPEG" and max(im.size) <= 1000 and len(raw) <= 400 * 1024
        inc = r.json()
        if inc.get("id"):
            DB.incoming.delete_one({"id": inc["id"]})


# Member photo upload compression
class TestPhotoUpload:
    def test_upload_photo_compressed(self, s):
        img = Image.blend(Image.effect_noise((3000, 4000), 50).convert("RGB"), Image.linear_gradient("L").resize((3000, 4000)).convert("RGB"), 0.5)
        buf = io.BytesIO(); img.save(buf, "JPEG", quality=95)
        assert len(buf.getvalue()) < 25 * 1024 * 1024
        r = s.post(f"{BASE_URL}/api/uploads/photo", files={"file": ("big.jpg", buf.getvalue(), "image/jpeg")}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        print(d)
        assert max(d["width"], d["height"]) <= 1080
        assert d["size"] <= 500 * 1024 or True  # informational, checked below
        path = d["url"].replace("/api/files/", "")
        f = s.get(f"{BASE_URL}{d['url']}")
        assert f.status_code == 200 and f.headers["content-type"] == "image/jpeg"
        DB.files.delete_one({"storage_path": path})
        assert d["size"] <= 500 * 1024, f"photo size {d['size']} > 500KB"


# DB indexes created at startup
class TestIndexes:
    @pytest.mark.parametrize("coll,keys", [
        ("books", ["title_1", "author_1", "created_at_1", "title_1_author_1", "id_1"]),
        ("members", ["name_1", "class_name_1", "student_id_1", "id_1"]),
        ("transactions", ["date_1", "action_1", "action_1_date_-1", "member_id_1_book_id_1"]),
        ("files", ["storage_path_1"]),
        ("visits", ["check_in_1", "date_-1_member_id_1"]),
        ("users", ["email_1"]),
    ])
    def test_index_exists(self, coll, keys):
        names = DB[coll].index_information().keys()
        for k in keys:
            assert k in names, f"{coll} missing {k}: {list(names)}"


# Service worker static check
class TestServiceWorker:
    def test_sw_served(self):
        r = requests.get(f"{BASE_URL}/service-worker.js")
        assert r.status_code == 200
        assert "precacheBuildChunks" in r.text and "asset-manifest.json" in r.text
