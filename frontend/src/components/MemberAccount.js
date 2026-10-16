import { useEffect, useState } from "react";
import { KeyRound, Trash2 } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

export function MemberAccount({ member, close, notify }) {
  const [acc, setAcc] = useState(undefined); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { api.get(`/members/${member.id}/account`).then((r) => { setAcc(r.data); setEmail(r.data?.email || ""); }).catch(() => setAcc(null)); }, [member.id]);
  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try { const { data } = await api.put(`/members/${member.id}/account`, { email, password }); setAcc(data); setPassword(""); notify(acc ? "Akun anggota diperbarui" : `Akun login untuk ${member.name} dibuat`); }
    catch (e2) { const d = e2.response?.data?.detail; setErr(Array.isArray(d) ? d.map((x) => x.msg).join(" ") : d || "Gagal menyimpan akun"); }
    finally { setBusy(false); }
  };
  const remove = async () => { if (!window.confirm(`Hapus akun login ${member.name}?`)) return; await api.delete(`/members/${member.id}/account`); setAcc(null); setEmail(""); notify("Akun login anggota dihapus"); };
  return <Modal title="Akun login anggota" close={close}>
    {acc === undefined ? <p className="muted">Memuat...</p> : <form className="modal-form" onSubmit={save} data-testid="member-account-form">
      <div className="lost-banner ok"><KeyRound size={20}/><div><b>{member.name}</b><small>{acc ? `Sudah punya akun · ${acc.email}` : "Belum punya akun login"} · masuk lewat /siswa</small></div></div>
      <label>Email login<input type="email" required data-testid="member-account-email-input" value={email} onChange={(e) => setEmail(e.target.value)}/></label>
      <label>{acc ? "Kata sandi baru (kosongkan jika tidak diganti)" : "Kata sandi"}<input type="password" minLength={6} required={!acc} data-testid="member-account-password-input" value={password} onChange={(e) => setPassword(e.target.value)}/></label>
      {err && <div className="error" data-testid="member-account-error">{err}</div>}
      <button className="primary full" disabled={busy} data-testid="save-member-account-button">{busy ? "Menyimpan..." : acc ? "Simpan perubahan" : "Buat akun"}</button>
      {acc && <button type="button" className="secondary full" data-testid="delete-member-account-button" onClick={remove}><Trash2 size={15}/> Hapus akun login</button>}
    </form>}
  </Modal>;
}
