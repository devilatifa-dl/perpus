import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from pymongo import MongoClient

_ROOT = Path(__file__).resolve().parents[2]
if not os.environ.get("REACT_APP_BACKEND_URL"):
    os.environ["REACT_APP_BACKEND_URL"] = dotenv_values(_ROOT / "frontend" / ".env")["REACT_APP_BACKEND_URL"]

_env = dotenv_values(_ROOT / "backend" / ".env")
_db = MongoClient(_env["MONGO_URL"])[_env["DB_NAME"]]
_snapshot = {}


def _is_controller(session):
    return not hasattr(session.config, "workerinput")


def pytest_sessionstart(session):
    # Snapshot the whole DB once (xdist controller only) so test data can be removed afterwards.
    if _is_controller(session):
        for name in _db.list_collection_names():
            _snapshot[name] = {d["_id"]: d for d in _db[name].find({})}


def pytest_sessionfinish(session):
    if not _is_controller(session) or not _snapshot:
        return
    for name in _db.list_collection_names():
        before = _snapshot.get(name, {})
        _db[name].delete_many({"_id": {"$nin": list(before)}})
        for _id, doc in before.items():
            _db[name].replace_one({"_id": _id}, doc, upsert=True)


@pytest.fixture(autouse=True)
def _clear_login_rate_limit():
    _db.login_attempts.delete_many({})
    yield
