"""Bantuan untuk data yang dicatat saat offline lalu disinkronkan (sirkulasi & pengunjung).

- client_id  : id unik dari perangkat -> mencegah data tercatat ganda saat sinkron diulang.
- client_time: waktu sebenarnya kejadian di perangkat (ISO). Dipakai bila wajar
               (tidak lebih dari 14 hari lalu dan tidak di masa depan), selain itu waktu server.
"""
from datetime import datetime, timedelta, timezone

MAX_AGE = timedelta(days=14)
FUTURE_SLACK = timedelta(minutes=5)


def client_dt(value):
    """Waktu kejadian dari perangkat (UTC) atau None bila kosong / tidak wajar."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if dt > now + FUTURE_SLACK or dt < now - MAX_AGE:
        return None
    return min(dt, now)
