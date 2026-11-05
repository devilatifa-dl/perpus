"""Pemisahan peringkat: siswa vs guru."""
from fastapi import HTTPException


def norm_audience(audience) -> str:
    a = (audience or "siswa").strip().lower()
    if a not in ("siswa", "guru"):
        raise HTTPException(400, "Pilihan peringkat harus siswa atau guru")
    return a


async def guru_member_ids(db) -> set:
    return {m["id"] for m in await db.members.find({"member_type": "guru"}, {"_id": 0, "id": 1}).to_list(None)}


def is_guru_row(row: dict, guru_ids: set) -> bool:
    """Baris kunjungan/transaksi milik guru: anggotanya bertipe guru, atau kelas tercatat "Guru" (riwayat lama)."""
    return row.get("member_id") in guru_ids or (row.get("class_name") or "").strip().lower() == "guru"
