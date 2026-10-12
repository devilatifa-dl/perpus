import os
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")
client = MongoClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
db.meta.update_one({"id": "seed"}, {"$set": {"id": "seed", "done": True}}, upsert=True)
print("meta.seed:", db.meta.find_one({"id": "seed"}, {"_id": 0}))
print("counts -> books:", db.books.count_documents({}), "members:", db.members.count_documents({}), "transactions:", db.transactions.count_documents({}))
client.close()
