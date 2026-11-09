// Fingerprint / biometrik admin memakai WebAuthn platform authenticator (sidik jari, Face ID,
// atau PIN perangkat). Kunci privat TIDAK pernah keluar dari HP — server hanya menyimpan
// public key. Dipakai sebagai gerbang cepat sebelum aksi sensitif; kata sandi tetap jadi
// cadangan bila perangkat tidak mendukung atau verifikasi gagal.

const b64url = (buf) => {
  const bytes = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

const fromB64url = (str) => {
  const pad = str.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(pad + "=".repeat((4 - (pad.length % 4)) % 4));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
};

/** Apakah perangkat punya sensor biometrik / authenticator platform? */
export async function biometricAvailable() {
  try {
    if (typeof window === "undefined" || !window.PublicKeyCredential) return false;
    if (!window.isSecureContext) return false;
    if (typeof PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable !== "function") return false;
    return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
  } catch {
    return false;
  }
}

/** Daftarkan fingerprint untuk user yang sedang login. */
export async function registerBiometric({ userId, userName, displayName }) {
  const { data } = await (await import("../lib")).api.post("/auth/webauthn/register/options");
  const publicKey = {
    ...data.options,
    challenge: fromB64url(data.options.challenge),
    user: { ...data.options.user, id: fromB64url(data.options.user.id) },
    authenticatorSelection: {
      authenticatorAttachment: "platform",
      userVerification: "required",
      residentKey: "preferred",
      requireResidentKey: false,
    },
    timeout: 60000,
  };
  const cred = await navigator.credentials.create({ publicKey });
  if (!cred) throw new Error("Pendaftaran dibatalkan");
  const payload = {
    id: cred.id,
    rawId: b64url(cred.rawId),
    type: cred.type,
    response: {
      clientDataJSON: b64url(cred.response.clientDataJSON),
      attestationObject: b64url(cred.response.attestationObject),
    },
    label: displayName || userName || "Perangkat ini",
  };
  await (await import("../lib")).api.post("/auth/webauthn/register", payload);
  return true;
}

/** Verifikasi fingerprint. Mengembalikan token sekali-pakai bila server menerima. */
export async function verifyBiometric() {
  const { data } = await (await import("../lib")).api.post("/auth/webauthn/login/options");
  if (!data.options?.allowCredentials?.length) throw new Error("Fingerprint belum didaftarkan di perangkat ini");
  const publicKey = {
    ...data.options,
    challenge: fromB64url(data.options.challenge),
    allowCredentials: data.options.allowCredentials.map((c) => ({ ...c, id: fromB64url(c.id) })),
    userVerification: "required",
    timeout: 60000,
  };
  const assertion = await navigator.credentials.get({ publicKey });
  if (!assertion) throw new Error("Verifikasi dibatalkan");
  const payload = {
    id: assertion.id,
    rawId: b64url(assertion.rawId),
    type: assertion.type,
    response: {
      clientDataJSON: b64url(assertion.response.clientDataJSON),
      authenticatorData: b64url(assertion.response.authenticatorData),
      signature: b64url(assertion.response.signature),
      userHandle: assertion.response.userHandle ? b64url(assertion.response.userHandle) : null,
    },
  };
  const res = await (await import("../lib")).api.post("/auth/webauthn/login", payload);
  if (!res.data?.ok) throw new Error("Verifikasi fingerprint ditolak");
  return res.data.token;
}

/** Apakah user ini sudah punya fingerprint terdaftar (di server). */
export async function biometricRegistered() {
  try {
    const { api } = await import("../lib");
    const { data } = await api.get("/auth/webauthn/status");
    return !!data?.registered;
  } catch {
    return false;
  }
}

export async function removeBiometric() {
  const { api } = await import("../lib");
  await api.delete("/auth/webauthn");
}
