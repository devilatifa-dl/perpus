import { useEffect, useRef, useState } from "react";
import { KeyRound, ShieldCheck, Save, Database, Download, Upload, Trash2, AlertTriangle } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

export function AccountManager({ user, close, notify }) {
  const isAdmin = user.role === "admin";
  const [cur, setCur] = useState(""); const [nw, setNw] = useState(""); const [conf, setConf] = useState("");
  const [savingOwn, setSavingOwn] = useState(false);
  const [users, setUsers] = useState([]); const [pwById, setPwById] = useState({}); const [savingId, setSavingId] = useState("");
  const [busyData, setBusyData] = useState(""); const [resetBooks, setResetBooks] = useState(false);
  const restoreRef = useRef(null);

  useEffect(() => {
    if (isAdmin) api.get("/users").then(r => setUsers(r.data)).catch(() => {});
  }, [isAdmin]);

  const backup = async () => {
    setBusyData("backup");
    try {
      const res = await api.get("/admin/backup.zip", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = `backup-perpustakaan-${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1500);
      notify("Cadangan data + semua laporan berhasil diunduh");
    } catch (err) {
      let msg = "Gagal mengunduh cadangan";
      try { msg = JSON.parse(await err.response.data.text()).detail || msg; } catch (e) { /* bukan JSON */ }
      notify(msg);
    } finally { setBusyData(""); }
  };

  const restore = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!window.confirm(`Pulihkan data dari "${file.name}"? Seluruh data saat ini akan digantikan oleh isi berkas cadangan.`)) return;
    setBusyData("restore");
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await api.post("/admin/restore", fd);
      const total = Object.values(res.data.restored || {}).reduce((a, b) => a + b, 0);
      notify(`Data berhasil dipulihkan (${total} entri). Memuat ulang...`);
      setTimeout(() => window.location.reload(), 1200);
    } catch (err) {
      notify(err.response?.data?.detail || "Gagal memulihkan data");
    } finally { setBusyData(""); }
  };

  const reset = async () => {
    const msg = resetBooks
      ? "Reset SEMUA data termasuk koleksi buku? Tindakan ini tidak dapat dibatalkan."
      : "Reset data (anggota, transaksi, pesanan, dll) kecuali koleksi buku? Tindakan ini tidak dapat dibatalkan.";
    if (!window.confirm(msg)) return;
    setBusyData("reset");
    try {
      await api.post("/admin/reset-data", { include_books: resetBooks });
      notify("Data berhasil direset. Memuat ulang...");
      setTimeout(() => window.location.reload(), 1200);
    } catch (err) {
      notify(err.response?.data?.detail || "Gagal mereset data");
    } finally { setBusyData(""); }
  };

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

      {isAdmin && <div className="account-users" data-testid="data-maintenance">
        <div className="account-section-head"><Database size={16}/> <span>Data &amp; pemeliharaan</span></div>
        <p className="account-hint">Unduh cadangan seluruh data, pulihkan dari berkas cadangan, atau reset data perpustakaan.</p>
        <p className="account-hint" data-testid="backup-contents-hint"><b>Unduh cadangan</b> menghasilkan satu berkas ZIP: data untuk pemulihan + semua laporan (Excel &amp; PDF) — transaksi, buku masuk, buku hilang, pengunjung, dan peringkat rajin berkunjung per bulan.</p>
        <div className="data-actions">
          <button type="button" className="secondary" data-testid="backup-data-button" disabled={busyData !== ""} onClick={backup}><Download size={15}/> {busyData === "backup" ? "Menyiapkan cadangan & laporan..." : "Unduh cadangan"}</button>
          <button type="button" className="secondary" data-testid="restore-data-button" disabled={busyData !== ""} onClick={() => restoreRef.current?.click()}><Upload size={15}/> {busyData === "restore" ? "Memulihkan..." : "Pulihkan data"}</button>
          <input ref={restoreRef} type="file" accept="application/json,.json,application/zip,.zip" hidden data-testid="restore-file-input" onChange={restore}/>
        </div>
        <div className="data-reset-zone">
          <label className="reset-books-check"><input type="checkbox" data-testid="reset-include-books" checked={resetBooks} onChange={e => setResetBooks(e.target.checked)}/> Ikut hapus koleksi buku</label>
          <button type="button" className="danger-btn" data-testid="reset-data-button" disabled={busyData !== ""} onClick={reset}><Trash2 size={15}/> {busyData === "reset" ? "Mereset..." : "Reset data"}</button>
          <p className="account-hint reset-warn"><AlertTriangle size={13}/> Reset &amp; pulihkan akan mengganti data saat ini dan tidak dapat dibatalkan.</p>
        </div>
      </div>}
    </div>
  </Modal>;
}
