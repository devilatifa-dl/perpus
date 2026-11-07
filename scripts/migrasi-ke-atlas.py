"""Migrasi seluruh data dari MongoDB lokal ke MongoDB Atlas.

Pakai:
    python scripts/migrasi-ke-atlas.py "mongodb+srv://user:pass@cluster.mongodb.net"

Skrip menyalin SEMUA koleksi apa adanya (termasuk foto anggota di koleksi `files`
dan cover buku di koleksi `books`), lalu memverifikasi jumlah dokumen.

Aman dijalankan berulang: koleksi tujuan dikosongkan dulu per koleksi sebelum
disalin, sehingga tidak ada duplikat.
"""

import asyncio
import sys

from motor.motor_asyncio import AsyncIOMotorClient

SUMBER = "mongodb://localhost:27017"
DB_SUMBER = "perpus"
DB_TUJUAN = "perpus"

# Koleksi sementara yang tidak perlu ikut dipindah
LEWATI = {"restore_chunks", "restore_uploads"}


def _nama_db(uri: str, bawaan: str) -> str:
    """Ambil nama database dari URI (mongodb+srv://host/nama?opts)."""
    tanpa_skema = uri.split("://", 1)[-1]
    if "/" not in tanpa_skema:
        return bawaan
    sisa = tanpa_skema.split("/", 1)[1]
    nama = sisa.split("?", 1)[0].strip()
    return nama or bawaan


async def main(uri_tujuan: str) -> int:
    klien_sumber = AsyncIOMotorClient(SUMBER, serverSelectionTimeoutMS=8000)
    klien_tujuan = AsyncIOMotorClient(uri_tujuan, serverSelectionTimeoutMS=20000)
    db_tujuan = _nama_db(uri_tujuan, DB_TUJUAN)

    try:
        await klien_sumber.admin.command("ping")
    except Exception as e:
        print(f"GAGAL konek MongoDB lokal: {e}")
        return 1

    try:
        await klien_tujuan.admin.command("ping")
    except Exception as e:
        print(f"GAGAL konek Atlas: {e}")
        print("Periksa: password benar, IP sudah diizinkan (0.0.0.0/0), nama cluster benar.")
        return 1

    db_s = klien_sumber[DB_SUMBER]
    db_t = klien_tujuan[db_tujuan]
    print(f"Database tujuan: {db_tujuan}")

    koleksi = sorted(await db_s.list_collection_names())
    print(f"Koleksi di sumber: {len(koleksi)}")
    print()

    total_dok = 0
    for nama in koleksi:
        if nama in LEWATI:
            print(f"  {nama:22s} dilewati (sementara)")
            continue

        dokumen = await db_s[nama].find({}).to_list(length=None)
        if not dokumen:
            print(f"  {nama:22s} kosong, dilewati")
            continue

        await db_t[nama].delete_many({})
        # batch kecil agar tidak melebihi batas 16 MB per perintah
        for i in range(0, len(dokumen), 100):
            await db_t[nama].insert_many(dokumen[i : i + 100], ordered=False)

        jumlah = await db_t[nama].count_documents({})
        status = "OK" if jumlah == len(dokumen) else "BEDA"
        print(f"  {nama:22s} {len(dokumen):6d} -> {jumlah:6d}  {status}")
        total_dok += jumlah

    print()
    print(f"Total dokumen dipindah: {total_dok}")

    # Verifikasi data penting
    print()
    print("=== Verifikasi ===")
    anggota = await db_t["members"].count_documents({})
    guru = await db_t["members"].count_documents({"member_type": "guru"})
    buku = await db_t["books"].count_documents({})
    foto = await db_t["files"].count_documents({"is_deleted": False})
    kunjungan = await db_t["visits"].count_documents({})
    pinjam = await db_t["transactions"].count_documents({})
    pengguna = await db_t["users"].count_documents({})

    print(f"  anggota    : {anggota} (guru: {guru})")
    print(f"  buku       : {buku}")
    print(f"  foto       : {foto}")
    print(f"  kunjungan  : {kunjungan}")
    print(f"  peminjaman : {pinjam}")
    print(f"  pengguna   : {pengguna}")

    # Pastikan foto benar-benar biner, bukan string base64
    contoh = await db_t["files"].find_one({"is_deleted": False}, {"_id": 0, "data": 1, "storage_path": 1})
    if contoh:
        jenis = type(contoh.get("data")).__name__
        print(f"  tipe data foto: {jenis} ({contoh.get('storage_path')})")
        if jenis != "bytes":
            print("  PERINGATAN: data foto bukan bytes. Foto bisa gagal tampil.")

    klien_sumber.close()
    klien_tujuan.close()

    if anggota == 0 or buku == 0:
        print()
        print("GAGAL: data utama kosong di Atlas.")
        return 1

    print()
    print("SELESAI. Data siap dipakai backend Render.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1].strip())))
