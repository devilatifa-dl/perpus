import { useEffect, useState } from "react";
import { KeyRound, ShieldCheck, Save } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

export function AccountManager({ user, close, notify }) {
  const isAdmin = user.role === "admin";
  const [cur, setCur] = useState(""); const [nw, setNw] = useState(""); const [conf, setConf] = useState("");
  const [savingOwn, setSavingOwn] = useState(false);
  const [users, setUsers] = useState([]); const [pwById, setPwById] = useState({}); const [savingId, setSavingId] = useState("");

  useEffect(() => {
    if (isAdmin) api.get("/users").then(r => setUsers(r.data)).catch(() => {});
  }, [isAdmin]);

  const changeOwn = async (e) => {
    e.preventDefault();
    if (nw !== conf) return notify("Konfirmasi kata sandi tidak cocok");
    if (nw.length < 6) return notify("Kata sandi baru minimal 6 karakter");
    setSavingOwn(true);
    try {
      await api.post("/account/password", { current_password: cur, new_password: nw });
      setCur(""); setNw(""); setConf("");
      notify("Kata sandi berhasil diperbarui");
    } catch (err) {
      notify(err.response?.data?.detail || "Gagal mengubah kata sandi");
    } finally { setSavingOwn(false); }
  };

  const setUserPw = async (u) => {
    const value = (pwById[u.id] || "").trim();
    if (value.length < 6) return notify("Kata sandi baru minimal 6 karakter");
    setSavingId(u.id);
    try {
      await api.put(`/users/${u.id}/password`, { new_password: value });
      setPwById({ ...pwById, [u.id]: "" });
      notify(`Kata sandi ${u.name} diperbarui`);
    } catch (err) {
      notify(err.response?.data?.detail || "Gagal mengubah kata sandi");
    } finally { setSavingId(""); }
  };

  return <Modal title="Akun & kata sandi" close={close}>
    <div className="account-manager" data-testid="account-manager">
      <form onSubmit={changeOwn} className="modal-form">
        <div className="account-section-head"><KeyRound size={16}/> <span>Ubah kata sandi saya ({user.role})</span></div>
        <label>Kata sandi lama<input type="password" data-testid="own-current-password" required value={cur} onChange={e => setCur(e.target.value)}/></label>
        <label>Kata sandi baru<input type="password" data-testid="own-new-password" required value={nw} onChange={e => setNw(e.target.value)}/></label>
        <label>Ulangi kata sandi baru<input type="password" data-testid="own-confirm-password" required value={conf} onChange={e => setConf(e.target.value)}/></label>
        <button className="primary full" data-testid="save-own-password" disabled={savingOwn}>{savingOwn ? "Menyimpan..." : "Simpan kata sandi"}</button>
      </form>

      {isAdmin && <div className="account-users">
        <div className="account-section-head"><ShieldCheck size={16}/> <span>Kelola kata sandi akun petugas &amp; admin</span></div>
        <p className="account-hint">Sebagai admin, Anda dapat menetapkan kata sandi baru untuk akun berikut.</p>
        {users.map(u => <div className="account-user-row" key={u.id} data-testid={`account-user-${u.id}`}>
          <div className="account-user-info"><b>{u.name}</b><small>{u.email} · {u.role}</small></div>
          <div className="account-user-action">
            <input type="password" placeholder="Kata sandi baru" data-testid={`set-password-input-${u.id}`} value={pwById[u.id] || ""} onChange={e => setPwById({ ...pwById, [u.id]: e.target.value })}/>
            <button type="button" className="secondary" data-testid={`set-password-button-${u.id}`} disabled={savingId === u.id} onClick={() => setUserPw(u)}><Save size={15}/> {savingId === u.id ? "..." : "Set"}</button>
          </div>
        </div>)}
      </div>}
    </div>
  </Modal>;
}
