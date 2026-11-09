"""Salin data production (perpus) ke database development (perpus_dev).

Jalankan dari folder backend:
    .venv\\Scripts\\python.exe sync_dev.py

Berguna sebelum menguji fitur baru agar data lokal sama dengan data nyata,
tanpa risiko mengubah data production.
"""
import asyncio
import os
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

COLLECTIONS = [
    "books", "members", "transactions", "incoming", "missing",
    "reservations", "stocktake", "shelves", "settings", "visits",
    "files", "users", "meta",
]
PROD_DB = "perpus"
DEV_DB = "perpus_dev"


def base_uri() -> str:
    """URI tanpa nama database, supaya bisa memilih perpus / perpus_dev."""
    uri = os.environ["MONGO_URL"]
    head, _, tail = uri.partition("?")
    # buang path database di akhir (mis. .../perpus_dev)
    if "/" in head.split("://", 1)[-1]:
        head = head.rsplit("/", 1)[0]
    return f"{head}/?{tail}" if tail else head


async def main() -> int:
    cli = AsyncIOMotorClient(base_uri(), serverSelectionTimeoutMS=20000)
    prod = cli.get_database(PROD_DB)
    dev = cli.get_database(DEV_DB)

    print(f"Menyalin {PROD_DB} -> {DEV_DB}")
    total = 0
    for name in COLLECTIONS:
        docs = await prod[name].find({}).to_list(None)
        await dev[name].delete_many({})
        if docs:
            await dev[name].insert_many(docs, ordered=False)
        total += len(docs)
        print(f"  {name:<14} {len(docs)}")

    print(f"\nSelesai. {total} dokumen disalin ke {DEV_DB}.")
    cli.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
