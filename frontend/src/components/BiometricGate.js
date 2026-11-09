import { useEffect, useState } from "react";
import { Fingerprint, KeyRound, Loader2, ShieldCheck, X } from "lucide-react";
import { biometricAvailable, biometricRegistered, registerBiometric, verifyBiometric } from "../lib/biometric";
import { Modal } from "./Shared";

/**
 * Gerbang aksi sensitif: coba fingerprint dulu, kata sandi sebagai cadangan.
 * Memanggil onVerified({ biometricToken }) bila berhasil.
 */
export function BiometricGate({ open, title, message, user, onVerified, onClose, requirePassword = false }) {
  const [supported, setSupported] = useState(null);
  const [registered, setRegistered] = useState(false);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (!open) return;
    setErr(""); setPassword(""); setBusy("");
    (async () => {
      const ok = await biometricAvailable();
      setSupported(ok);
      if (ok) setRegistered(await biometricRegistered());
      setShowPassword(requirePassword || !ok);
    })();
  }, [open, requirePassword]);

  if (!open) return null;

  const doFingerprint = async () => {
    setBusy("fp"); setErr("");
    try {
      const token = await verifyBiometric();
      onVerified({ biometricToken: token, viaFingerprint: true });
    } catch (e) {
      setErr(e?.message || "Fingerprint gagal. Coba lagi atau pakai kata sandi.");
      setShowPassword(true);
    } finally {
      setBusy("");
    }
  };

  const doRegister = async () => {
    setBusy("reg"); setErr("");
    try {
      await registerBiometric({ userId: user?.id, userName: user?.email, displayName: user?.name });
      setRegistered(true);
      await doFingerprint();
    } catch (e) {
      setErr(e?.message || "Gagal mendaftarkan fingerprint");
    } finally {
      setBusy("");
    }
  };

  const submitPassword = (e) => {
    e.preventDefault();
    if (!password) { setErr("Masukkan kata sandi admin"); return; }
    onVerified({ password, viaFingerprint: false });
  };

  return <Modal title={title || "Verifikasi admin"} close={onClose}>
    <div className="bio-gate" data-testid="biometric-gate">
      <div className="bio-head">
        <div className={`bio-icon ${registered ? "on" : ""}`}><Fingerprint size={30}/></div>
        <p className="muted">{message || "Aksi ini hanya untuk admin. Verifikasi dulu untuk melanjutkan."}</p>
      </div>

      {err && <div className="error" data-testid="bio-error">{err}</div>}

      {supported === null && <p className="muted"><Loader2 size={14} className="spin"/> Memeriksa perangkat...</p>}

      {supported && !registered && !showPassword && (
        <button className="primary full" data-testid="bio-register-button" disabled={!!busy} onClick={doRegister}>
          {busy === "reg" ? <Loader2 size={17} className="spin"/> : <Fingerprint size={17}/>} Daftarkan fingerprint
        </button>
      )}

      {supported && registered && (
        <button className="primary full" data-testid="bio-verify-button" disabled={!!busy} onClick={doFingerprint}>
          {busy === "fp" ? <Loader2 size={17} className="spin"/> : <Fingerprint size={17}/>} Verifikasi fingerprint
        </button>
      )}

      {supported && !showPassword && (
        <button className="text-button" data-testid="bio-use-password" onClick={() => setShowPassword(true)}>
          <KeyRound size={14}/> Pakai kata sandi
        </button>
      )}

      {showPassword && (
        <form onSubmit={submitPassword} className="bio-password" data-testid="bio-password-form">
          <label>Kata sandi admin
            <input type="password" autoFocus data-testid="bio-password-input" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Masukkan kata sandi"/>
          </label>
          <button className="primary full" data-testid="bio-password-submit" disabled={!!busy}>
            <ShieldCheck size={17}/> Lanjutkan
          </button>
          {supported && registered && (
            <button type="button" className="text-button" data-testid="bio-back-fingerprint" onClick={() => { setShowPassword(false); setErr(""); }}>
              <Fingerprint size={14}/> Kembali ke fingerprint
            </button>
          )}
        </form>
      )}

      {!supported && <p className="muted" data-testid="bio-unsupported">Perangkat ini belum mendukung fingerprint. Gunakan kata sandi.</p>}
    </div>
  </Modal>;
}

export { X };
