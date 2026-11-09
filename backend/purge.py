"""Hapus laporan lama (manual terpilih / per tahun / rentang tanggal). Hanya admin, cukup konfirmasi (tanpa kode email)."""
import uuid
from datetime import datetime, date
from typing import List, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from reports_pdf import WIB, build_loans, render_report_xlsx

TYPES = {"transaksi": "Transaksi peminjaman", "kunjungan": "Pengunjung", "masuk": "Buku masuk", "hilang": "Buku hilang"}


class PurgeSelect(BaseModel):
    type: str
    mode: str = Field("tahun", pattern="^(tahun|rentang|pilih)$")
    year: Optional[int] = None
    start: Optional[str] = None
    end: Optional[str] = None
    ids: List[str] = []


class PurgeInput(PurgeSelect):
    code: str = ""
    password: str = ""
    biometric_token: str = ""


def _day(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
    return (dt.astimezone(WIB) if dt.tzinfo else dt).date()


def _range(sel: PurgeSelect):
    if sel.mode == "tahun":
        if not sel.year or sel.year < 2000 or sel.year > 2100:
            raise HTTPException(400, "Pilih tahun yang valid")
        return date(sel.year, 1, 1), date(sel.year, 12, 31), f"Tahun {sel.year}"
    if sel.mode == "rentang":
        try:
            a, b = date.fromisoformat(sel.start or ""), date.fromisoformat(sel.end or "")
        except ValueError:
            raise HTTPException(400, "Tanggal mulai dan sampai wajib diisi")
        if a > b:
            raise HTTPException(400, "Tanggal mulai tidak boleh setelah tanggal sampai")
        return a, b, f"{a.strftime('%d-%m-%Y')} s.d. {b.strftime('%d-%m-%Y')}"
    if not sel.ids:
        raise HTTPException(400, "Belum ada data yang dipilih")
    return None, None, f"{len(sel.ids)} data terpilih"


def build_router(db, current_user, verify_reset_code, visits_auto_close):
    r = APIRouter()

    def admin_only(user):
        if user["role"] != "admin":
            raise HTTPException(403, "Hanya admin yang dapat menghapus laporan")

    async def collect(sel: PurgeSelect):
        """Kembalikan (rows untuk cadangan, id dokumen yang dihapus, jumlah dilindungi, label)."""
        if sel.type not in TYPES:
            raise HTTPException(400, "Jenis laporan tidak valid")
        start, end, label = _range(sel)
        ids = set(sel.ids)

        def hit(row_id, value):
            if sel.mode == "pilih":
                return row_id in ids
            d = _day(value)
            return d is not None and start <= d <= end

        protected = 0
        if sel.type == "transaksi":
            loans = build_loans(await db.transactions.find({}, {"_id": 0}).to_list(None))
            rows, del_ids = [], []
            for l in loans:
                if not hit(l["id"], l.get("borrowed_at") or l.get("returned_at")):
                    continue
                if l["status"] == "Dipinjam":
                    protected += 1  # buku masih dipinjam: jangan dihapus agar stok tetap benar
                    continue
                rows.append(l); del_ids.append(l["id"])
                if l.get("return_id"):
                    del_ids.append(l["return_id"])
            need = list({l["member_id"] for l in rows if not l.get("class_name") and l.get("member_id")})
            if need:
                info = {m["id"]: m.get("class_name", "") for m in await db.members.find({"id": {"$in": need}}, {"_id": 0, "id": 1, "class_name": 1}).to_list(None)}
                for l in rows:
                    if not l.get("class_name"):
                        l["class_name"] = info.get(l.get("member_id"), "")
            return rows, del_ids, protected, label
        if sel.type == "kunjungan":
            await visits_auto_close()
            all_rows = await db.visits.find({}, {"_id": 0}).sort("check_in", -1).to_list(None)
            rows = []
            for v in all_rows:
                if not hit(v["id"], v.get("check_in")):
                    continue
                if not v.get("check_out"):
                    protected += 1  # masih di dalam perpustakaan
                    continue
                rows.append(v)
            return rows, [v["id"] for v in rows], protected, label
        coll = db.incoming if sel.type == "masuk" else db.missing
        all_rows = await coll.find({}, {"_id": 0}).sort("date", -1).to_list(None)
        rows = [x for x in all_rows if hit(x["id"], x.get("date"))]
        return rows, [x["id"] for x in rows], 0, label

    @r.post("/reports/purge/preview")
    async def purge_preview(sel: PurgeSelect, user=Depends(current_user)):
        admin_only(user)
        rows, _, protected, label = await collect(sel)
        return {"type": sel.type, "type_label": TYPES[sel.type], "label": label, "count": len(rows), "protected": protected}

    @r.post("/reports/purge/backup.xlsx")
    async def purge_backup(sel: PurgeSelect, user=Depends(current_user)):
        admin_only(user)
        rows, _, _, label = await collect(sel)
        settings = await db.settings.find_one({"id": "main"}, {"_id": 0}) or {}
        data = render_report_xlsx(sel.type, f"Arsip sebelum dihapus — {label}", rows, settings, user["name"])
        fname = f"arsip-{sel.type}-{datetime.now(WIB).strftime('%Y%m%d-%H%M')}.xlsx"
        return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})

    @r.post("/reports/purge")
    async def purge(data: PurgeInput, user=Depends(current_user)):
        admin_only(user)
        # Fingerprint lebih dulu; kata sandi jadi cadangan.
        from webauthn_auth import consume_biometric_token
        if not await consume_biometric_token(db, user["id"], data.biometric_token):
            if not data.password or not bcrypt.checkpw(data.password.encode(), user["password_hash"].encode()):
                raise HTTPException(400, "Sandi admin salah. Laporan tidak dihapus.")
        rows, del_ids, protected, label = await collect(data)
        if not rows:
            raise HTTPException(400, "Tidak ada data yang bisa dihapus pada pilihan ini")
        coll = {"transaksi": db.transactions, "kunjungan": db.visits, "masuk": db.incoming, "hilang": db.missing}[data.type]
        res = await coll.delete_many({"id": {"$in": del_ids}})
        await db.purge_logs.insert_one({"id": "PG-" + str(uuid.uuid4())[:8].upper(), "type": data.type, "label": label, "rows": len(rows),
                                        "documents": res.deleted_count, "by": user["name"], "at": datetime.now(WIB).isoformat()})
        return {"ok": True, "deleted": len(rows), "protected": protected, "label": label, "type_label": TYPES[data.type]}

    @r.get("/reports/purge/logs")
    async def purge_logs(user=Depends(current_user)):
        admin_only(user)
        return await db.purge_logs.find({}, {"_id": 0}).sort("at", -1).to_list(50)

    return r
