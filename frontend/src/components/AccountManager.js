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

  const [restoreFile, setRestoreFile] = useState(null); const [restoreTo, setRestoreTo] = useState(""); const [restoreCode, setRestoreCode] = useState("");

  const sendCode = async (purpose) => {
    const { data } = await api.post(`/admin/reset-code?purpose=${purpose}`);
    notify(`Kode verifikasi dikirim ke ${data.sent_to}`);
    return data.sent_to;
  };

  const pickRestore = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!window.confirm(`Pulihkan data dari "${file.name}"? Seluruh data saat ini akan digantikan oleh isi berkas cadangan.`)) return;
    setBusyData("restore-code");
    try { setRestoreTo(await sendCode("restore")); setRestoreFile(file); setRestoreCode(""); }
    catch (err) { notify(err.response?.data?.detail || "Gagal mengirim kode verifikasi"); }
    finally { setBusyData(""); }
  };

  const [restoreProg, setRestoreProg] = useState(null);
  // Berkas dikirim dalam potongan kecil sehingga cadangan berukuran berapa pun bisa dipulihkan.
  const restore = async () => {
    setBusyData("restore");
    const warn = (e) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    try {
      const guessChunk = 8 * 1024 * 1024;
      const chunks = Math.max(1, Math.ceil(restoreFile.size / guessChunk));
      setRestoreProg({ pct: 0, text: "Memverifikasi kode..." });
      const { data: st } = await api.post("/admin/restore/start", { code: restoreCode, filename: restoreFile.name, size: restoreFile.size, chunks });
      const size = st.chunk_size || guessChunk;
      if (size !== guessChunk) throw new Error("Ukuran potongan tidak cocok, muat ulang halaman lalu coba lagi");
      for (let i = 0; i < chunks; i++) {
        const part = restoreFile.slice(i * size, Math.min(restoreFile.size, (i + 1) * size));
        let ok = false, lastErr = null;
        for (let attempt = 0; attempt < 4 && !ok; attempt++) {
          try {
            await api.put("/admin/restore/chunk", part, { params: { upload_id: st.upload_id, index: i }, headers: { "Content-Type": "application/octet-stream" } });
            ok = true;
          } catch (err) {
            lastErr = err;
            if (err.response && err.response.status < 500) break;
            await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
          }
        }
        if (!ok) throw lastErr;
        const pct = Math.round(((i + 1) / chunks) * 100);
        setRestoreProg({ pct, text: `Mengunggah ${fmtSize(Math.min(restoreFile.size, (i + 1) * size))} dari ${fmtSize(restoreFile.size)}` });
      }
      await api.post("/admin/restore/finish", { upload_id: st.upload_id });
      const STAGE = { menyiapkan: "Menyiapkan berkas", memeriksa: "Memeriksa isi cadangan", memuat: "Memuat data", mengganti: "Mengganti data lama" };
      let fails = 0;
      for (;;) {
        await new Promise((r) => setTimeout(r, 2000));
        let job;
        try { job = (await api.get(`/admin/restore/status/${st.upload_id}`)).data; fails = 0; }
        catch (err) { if (++fails > 30) throw err; continue; }
        if (job.status === "done") {
          const total = Object.values(job.restored || {}).reduce((a, b) => a + b, 0);
          setRestoreProg({ pct: 100, text: `Selesai: ${total} entri dipulihkan`, done: true });
          notify(`Data berhasil dipulihkan (${total} entri). Memuat ulang...`);
          window.removeEventListener("beforeunload", warn);
          setTimeout(() => window.location.reload(), 1500);
          return;
        }
        if (job.status === "error") throw new Error(job.error || "Gagal memulihkan data");
        const pr = job.progress || {};
        setRestoreProg({ pct: 100, processing: true, text: `${STAGE[pr.stage] || "Memproses"}${pr.collection ? ` · ${pr.collection}` : ""}${pr.inserted ? ` · ${pr.inserted} entri` : ""}...` });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Gagal memulihkan data";
      setRestoreProg({ pct: 0, text: msg, error: true });
      notify(msg);
    } finally {
      window.removeEventListener("beforeunload", warn);
      setBusyData("");
    }
  };

  const [codeTo, setCodeTo] = useState(""); const [code, setCode] = useState("");

  const requestCode = async () => {
    const msg = resetBooks
      ? "Reset SEMUA data termasuk koleksi buku? Tindakan ini tidak dapat dibatalkan."
      : "Reset data (anggota, transaksi, pesanan, dll) kecuali koleksi buku? Tindakan ini tidak dapat dibatalkan.";
    if (!window.confirm(msg)) return;
    setBusyData("code");
    try {
      setCodeTo(await sendCode("reset")); setCode("");
    } catch (err) {
      notify(err.response?.data?.detail || "Gagal mengirim kode verifikasi");
    } finally { setBusyData(""); }
  };

  const reset = async () => {
    if (code.trim().length !== 6) return notify("Masukkan 6 digit kode verifikasi");
    setBusyData("reset");
    try {
      await api.post("/admin/reset-data", { include_books: resetBooks, code: code.trim() });
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
          <button type="button" className="secondary" data-testid="restore-data-button" disabled={busyData !== ""} onClick={() => restoreRef.current?.click()}><Upload size={15}/> {busyData === "restore-code" ? "Mengirim kode..." : busyData === "restore" ? "Memulihkan..." : "Pulihkan data"}</button>
          <input ref={restoreRef} type="file" accept="application/json,.json,application/zip,.zip" hidden data-testid="restore-file-input" onChange={pickRestore}/>
        </div>
        {restoreFile && <CodeBox prefix="restore" to={restoreTo} code={restoreCode} setCode={setRestoreCode} busy={busyData !== ""} label={busyData === "restore" ? "Memulihkan..." : "Konfirmasi pulihkan"} note={`Berkas: ${restoreFile.name} (${fmtSize(restoreFile.size)})`} onConfirm={restore} onCancel={() => { setRestoreFile(null); setRestoreTo(""); setRestoreCode(""); setRestoreProg(null); }}/>}
        {restoreProg && <div className={`restore-progress${restoreProg.error ? " error" : ""}${restoreProg.done ? " done" : ""}`} data-testid="restore-progress">
          <div className="restore-progress-track"><div className={restoreProg.processing ? "busy" : ""} style={{ width: `${restoreProg.pct}%` }}/></div>
          <p className="account-hint" data-testid="restore-progress-text">{restoreProg.text}</p>
        </div>}
        <p className="account-hint" data-testid="restore-size-hint">Cadangan berukuran berapa pun bisa dipulihkan. Berkas besar dikirim bertahap — jangan tutup halaman sampai selesai.</p>
        <div className="data-reset-zone">
          <label className="reset-books-check"><input type="checkbox" data-testid="reset-include-books" checked={resetBooks} onChange={e => setResetBooks(e.target.checked)}/> Ikut hapus koleksi buku</label>
          <button type="button" className="danger-btn" data-testid="reset-data-button" disabled={busyData !== ""} onClick={requestCode}><Trash2 size={15}/> {busyData === "code" ? "Mengirim kode..." : codeTo ? "Kirim ulang kode" : "Reset data"}</button>
          {codeTo && <CodeBox prefix="reset" to={codeTo} code={code} setCode={setCode} busy={busyData !== ""} label={busyData === "reset" ? "Mereset..." : "Konfirmasi reset"} onConfirm={reset} onCancel={() => { setCodeTo(""); setCode(""); }}/>}
          <p className="account-hint reset-warn"><AlertTriangle size={13}/> Reset &amp; pulihkan akan mengganti data saat ini dan tidak dapat dibatalkan.</p>
        </div>
      </div>}
    </div>
  </Modal>;
}

function fmtSize(n) {
  if (!n && n !== 0) return "-";
  if (n >= 1024 * 1024 * 1024) return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
  if (n >= 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(n / 1024))} KB`;
}

function CodeBox({ prefix, to, code, setCode, busy, label, note, onConfirm, onCancel }) {
  return <div className={`${prefix}-code-box`} data-testid={`${prefix}-code-box`} style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginTop: 10 }}>
    <p className="account-hint" data-testid={`${prefix}-code-sent-to`} style={{ width: "100%" }}>{note ? `${note}. ` : ""}Kode verifikasi 6 digit sudah dikirim ke <b>{to}</b>. Berlaku 10 menit.</p>
    <input data-testid={`${prefix}-code-input`} inputMode="numeric" maxLength={6} placeholder="Kode verifikasi" value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ""))} style={{ maxWidth: 180, letterSpacing: 4 }}/>
    <button type="button" className="danger-btn" data-testid={`${prefix}-confirm-button`} disabled={busy || code.length !== 6} onClick={onConfirm}>{label}</button>
    <button type="button" className="secondary" data-testid={`${prefix}-cancel-button`} disabled={busy} onClick={onCancel}>Batal</button>
  </div>;
}
