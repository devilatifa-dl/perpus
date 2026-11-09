"""Fingerprint / biometrik admin lewat WebAuthn (platform authenticator).

Kunci privat tetap di perangkat pengguna; server hanya menyimpan public key.
Dipakai sebagai gerbang cepat sebelum aksi sensitif (akun & sandi, reset data,
hapus laporan). Kata sandi tetap tersedia sebagai cadangan.
"""
import base64
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

RP_NAME = "Ruang Baca SMANSA"
CHALLENGE_TTL = 300  # detik


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64url(value: str) -> bytes:
    pad = value.replace("-", "+").replace("_", "/")
    return base64.b64decode(pad + "=" * (-len(pad) % 4))


def _now():
    return datetime.now(timezone.utc)


class RegisterPayload(BaseModel):
    id: str
    rawId: str
    type: str = "public-key"
    response: dict
    label: str = ""


class LoginPayload(BaseModel):
    id: str
    rawId: str
    type: str = "public-key"
    response: dict


def build_router(db, current_user):
    r = APIRouter()

    def rp_id(request: Request) -> str:
        """Domain efektif (tanpa port) — harus sama dengan yang dipakai browser."""
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost"
        return host.split(":")[0]

    def origin(request: Request) -> str:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "https"
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost"
        return f"{proto}://{host}"

    async def save_challenge(user_id: str, challenge: bytes, kind: str):
        await db.webauthn_challenges.delete_many({"user_id": user_id, "kind": kind})
        await db.webauthn_challenges.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "kind": kind,
            "challenge": _b64url(challenge),
            "created_at": _now(),
        })

    async def take_challenge(user_id: str, kind: str) -> bytes:
        doc = await db.webauthn_challenges.find_one_and_delete({"user_id": user_id, "kind": kind})
        if not doc:
            raise HTTPException(400, "Sesi fingerprint kedaluwarsa. Coba lagi.")
        created = doc.get("created_at")
        if isinstance(created, datetime):
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if _now() - created > timedelta(seconds=CHALLENGE_TTL):
                raise HTTPException(400, "Sesi fingerprint kedaluwarsa. Coba lagi.")
        return _unb64url(doc["challenge"])

    @r.get("/auth/webauthn/status")
    async def status(user=Depends(current_user)):
        count = await db.webauthn_credentials.count_documents({"user_id": user["id"]})
        return {"registered": count > 0, "count": count}

    @r.post("/auth/webauthn/register/options")
    async def register_options(request: Request, user=Depends(current_user)):
        if user.get("role") != "admin":
            raise HTTPException(403, "Fingerprint hanya untuk admin")
        existing = await db.webauthn_credentials.find({"user_id": user["id"]}, {"_id": 0, "credential_id": 1}).to_list(50)
        options = generate_registration_options(
            rp_id=rp_id(request),
            rp_name=RP_NAME,
            user_id=user["id"].encode(),
            user_name=user.get("email") or user["id"],
            user_display_name=user.get("name") or "Admin",
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=_unb64url(c["credential_id"]))
                for c in existing
            ],
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                user_verification=UserVerificationRequirement.REQUIRED,
                resident_key=ResidentKeyRequirement.PREFERRED,
            ),
        )
        await save_challenge(user["id"], options.challenge, "register")
        import json
        return {"options": json.loads(options_to_json(options))}

    @r.post("/auth/webauthn/register")
    async def register(payload: RegisterPayload, request: Request, user=Depends(current_user)):
        if user.get("role") != "admin":
            raise HTTPException(403, "Fingerprint hanya untuk admin")
        challenge = await take_challenge(user["id"], "register")
        try:
            verified = verify_registration_response(
                credential={
                    "id": payload.id,
                    "rawId": payload.rawId,
                    "type": payload.type,
                    "response": payload.response,
                },
                expected_challenge=challenge,
                expected_rp_id=rp_id(request),
                expected_origin=origin(request),
                require_user_verification=True,
            )
        except Exception as e:
            raise HTTPException(400, f"Pendaftaran fingerprint gagal: {e}")

        await db.webauthn_credentials.update_one(
            {"credential_id": _b64url(verified.credential_id)},
            {"$set": {
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "credential_id": _b64url(verified.credential_id),
                "public_key": _b64url(verified.credential_public_key),
                "sign_count": verified.sign_count,
                "label": (payload.label or "Perangkat ini")[:80],
                "created_at": _now(),
            }},
            upsert=True,
        )
        return {"ok": True}

    @r.post("/auth/webauthn/login/options")
    async def login_options(request: Request, user=Depends(current_user)):
        creds = await db.webauthn_credentials.find({"user_id": user["id"]}, {"_id": 0, "credential_id": 1}).to_list(50)
        options = generate_authentication_options(
            rp_id=rp_id(request),
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=_unb64url(c["credential_id"]))
                for c in creds
            ],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        await save_challenge(user["id"], options.challenge, "login")
        import json
        return {"options": json.loads(options_to_json(options))}

    @r.post("/auth/webauthn/login")
    async def login(payload: LoginPayload, request: Request, user=Depends(current_user)):
        cred = await db.webauthn_credentials.find_one({"user_id": user["id"], "credential_id": payload.id})
        if not cred:
            raise HTTPException(404, "Fingerprint belum terdaftar di perangkat ini")
        challenge = await take_challenge(user["id"], "login")
        try:
            verified = verify_authentication_response(
                credential={
                    "id": payload.id,
                    "rawId": payload.rawId,
                    "type": payload.type,
                    "response": payload.response,
                },
                expected_challenge=challenge,
                expected_rp_id=rp_id(request),
                expected_origin=origin(request),
                credential_public_key=_unb64url(cred["public_key"]),
                credential_current_sign_count=cred.get("sign_count", 0),
                require_user_verification=True,
            )
        except Exception as e:
            raise HTTPException(400, f"Verifikasi fingerprint gagal: {e}")

        await db.webauthn_credentials.update_one(
            {"credential_id": payload.id},
            {"$set": {"sign_count": verified.new_sign_count, "last_used_at": _now()}},
        )
        # Tanda tangan singkat: aksi sensitif berikutnya boleh langsung tanpa fingerprint ulang.
        token = secrets.token_urlsafe(24)
        await db.webauthn_sessions.insert_one({
            "id": token,
            "user_id": user["id"],
            "created_at": _now(),
            "expires_at": _now() + timedelta(minutes=5),
        })
        return {"ok": True, "token": token}

    @r.delete("/auth/webauthn")
    async def remove(user=Depends(current_user)):
        res = await db.webauthn_credentials.delete_many({"user_id": user["id"]})
        return {"ok": True, "removed": res.deleted_count}

    return r


async def consume_biometric_token(db, user_id: str, token: str) -> bool:
    """Pakai sekali: token fingerprint yang valid & belum kedaluwarsa."""
    if not token:
        return False
    doc = await db.webauthn_sessions.find_one_and_delete({"id": token, "user_id": user_id})
    if not doc:
        return False
    exp = doc.get("expires_at")
    if isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < _now():
            return False
    return True
