import asyncio, bcrypt, sys
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    db = AsyncIOMotorClient('mongodb://localhost:27017')['test_database']
    if len(sys.argv) > 1 and sys.argv[1] == 'code':
        await db.reset_codes.update_one({'id': 'purge'}, {'$set': {'id': 'purge', 'code_hash': bcrypt.hashpw(b'123456', bcrypt.gensalt()).decode(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(), 'sent_at': '2000-01-01T00:00:00+00:00', 'attempts': 0}}, upsert=True)
        print('code 123456 set'); return
    tx, vs, inc, ms = [], [], [], []
    for i in range(6):
        d = datetime(2024, 3 + i, 10, 3, 0, tzinfo=timezone.utc)
        tx.append({"id": f"TRX-OLD{i}P", "member_id": "MB-2024002", "member_name": "Siti Rahma", "class_name": "X IPS 1", "book_id": "BK-1042", "book_title": "Laskar Pelangi", "action": "pinjam", "date": d.isoformat()})
        tx.append({"id": f"TRX-OLD{i}K", "member_id": "MB-2024002", "member_name": "Siti Rahma", "class_name": "X IPS 1", "book_id": "BK-1042", "book_title": "Laskar Pelangi", "action": "kembali", "date": (d + timedelta(days=3)).isoformat()})
        vs.append({"id": f"VS-OLD{i}", "kind": "anggota", "member_id": "MB-2024002", "student_id": "24002", "name": "Siti Rahma", "class_name": "X IPS 1", "purpose": "Membaca", "origin": "", "photo": "", "check_in": d.isoformat(), "check_out": (d + timedelta(hours=1)).isoformat(), "checkout_type": "scan", "duration_min": 60, "date": d.date().isoformat(), "recorded_by": "seed"})
        inc.append({"id": f"IN-OLD{i}", "title": f"Buku Lama {i}", "author": "Anon", "category": "Umum", "shelf": "A1", "quantity": 2, "detail": "2 eksemplar", "source": "Hibah", "date": d.date().isoformat(), "status": "Tersimpan", "book_ids": [], "book_id": "", "merged": False, "recorded_by": "seed", "created_at": d.isoformat()})
        ms.append({"id": f"LS-OLD{i}", "book_id": "BK-1042", "title": "Laskar Pelangi", "code": "BK-1042", "detail": "1 eksemplar", "date": d.isoformat(), "status": "Ditemukan", "reported_by": "seed"})
    for coll, rows in ((db.transactions, tx), (db.visits, vs), (db.incoming, inc), (db.missing, ms)):
        await coll.delete_many({"id": {"$in": [r["id"] for r in rows]}})
        await coll.insert_many(rows)
    print('seeded 2024 data: 6 loans, 6 visits, 6 incoming, 6 missing')

asyncio.run(main())
