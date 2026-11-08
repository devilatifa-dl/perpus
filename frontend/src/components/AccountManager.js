import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import JSZip from "jszip";
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

  const saveBlob = (blob, name) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1500);
  };
  const errMsg = async (err, fallback) => {
    if (!err?.response && err?.message) return err.message;
    try { return JSON.parse(await err.response.data.text()).detail || fallback; } catch (e) { return fallback; }
  };

  const fetchZip = async () => {
    const res = await api.get("/admin/backup.zip", { responseType: "blob", timeout: 0 });
    const expected = Number(res.headers?.["x-backup-bytes"] || 0);
    // Pastikan berkas utuh sebelum disimpan (unduhan yang terputus membuat ZIP rusak saat dipulihkan)
    if ((expected && res.data.size !== expected) || !(await isCompleteZip(res.data))) {
      const e = new Error(`Unduhan cadangan terpotong (${fmtSize(res.data.size)}${expected ? ` dari ${fmtSize(expected)}` : ""})`);
      e.truncated = true; throw e;
    }
    return res.data;
  };
  const fetchJson = async () => {
    const res = await api.get("/admin/backup", { responseType: "blob", timeout: 0 });
    const text = await res.data.text();
    JSON.parse(text); // gagal bila terpotong
    return new Blob([text], { type: "application/json" });
  };

  // Satu tombol: ZIP lengkap (data + laporan). Bila unduhan ZIP gagal/terpotong, coba sekali lagi,
  // lalu otomatis simpan data cadangan (.json) yang tetap cukup untuk "Pulihkan data".
  const backup = async () => {
    setBusyData("backup");
    const day = new Date().toISOString().slice(0, 10);
    try {
      let zip = null, lastErr = null;
      for (let attempt = 0; attempt < 2 && !zip; attempt++) {
        try { zip = await fetchZip(); } catch (err) {
          lastErr = err;
          if (err.response && err.response.status < 500) throw err; // mis. bukan admin
        }
      }
      if (zip) {
        saveBlob(zip, `backup-perpustakaan-${day}.zip`);
        notify(`Cadangan data + semua laporan berhasil diunduh (${fmtSize(zip.size)}, berkas utuh)`);
        return;
      }
      setBusyData("backup-json");
      const json = await fetchJson();
      saveBlob(json, `data-cadangan-${day}.json`);
      notify(`${lastErr?.truncated ? "Unduhan ZIP terputus" : "ZIP gagal diunduh"}, jadi data cadangan disimpan sebagai berkas .json (${fmtSize(json.size)}). Berkas ini cukup untuk Pulihkan data.`);
    } catch (err) {
      notify(err instanceof SyntaxError ? "Unduhan data terputus. Periksa koneksi lalu coba lagi." : await errMsg(err, "Gagal mengunduh cadangan"));
    } finally { setBusyData(""); }
  };

  const [restoreFile, setRestoreFile] = useState(null);

  const pickRestore = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!window.confirm(`Pulihkan data dari "${file.name}"? Seluruh data saat ini akan digantikan oleh isi berkas cadangan.`)) return;
    setRestoreFile(file);
    restore(file);
  };

  const [restoreProg, setRestoreProg] = useState(null);

  // Baca isi cadangan (.zip dari "Unduh cadangan" atau .json lama) langsung di browser.
  const readBackup = async (file) => {
    const isZip = /\.zip$/i.test(file.name) || (await file.slice(0, 2).text()) === "PK";
    let text;
    if (isZip) {
      const zip = await JSZip.loadAsync(file);
      const member = Object.keys(zip.files).find((n) => n === "data-cadangan.json" || n.endsWith("/data-cadangan.json"));
      if (!member) throw new Error("ZIP cadangan tidak berisi data-cadangan.json");
      text = await zip.files[member].async("string");
    } else {
      text = await file.text();
    }
    let parsed;
    try { parsed = JSON.parse(text); } catch (e) { throw new Error("Isi berkas cadangan tidak lengkap (terpotong) atau bukan JSON. Unduh ulang cadangan lalu coba lagi."); }
    const cols = parsed && parsed.collections;
    if (!cols || typeof cols !== "object") throw new Error("Struktur berkas cadangan tidak dikenali");
    const names = Object.keys(cols).filter((n) => Array.isArray(cols[n]));
    if (!names.length) throw new Error("Berkas cadangan tidak berisi data perpustakaan");
    return { cols, names };
  };

  // Data dikirim per potongan kecil (di bawah 2 MB) sehingga setiap permintaan cepat selesai dan
  // tidak terkena batas waktu hosting serverless. Data lama baru diganti pada langkah "commit".
  const restore = async (restoreFile) => {
    setBusyData("restore");
    const warn = (e) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    let uploadId = null;
    try {
      setRestoreProg({ pct: 0, text: `Membaca ${restoreFile.name}...` });
      const { cols, names } = await readBackup(restoreFile);
      const total = names.reduce((a, n) => a + cols[n].length, 0);
      const { data: st } = await api.post("/admin/restore/begin", { filename: restoreFile.name, size: restoreFile.size, collections: names });
      uploadId = st.upload_id;
      const MAX_BYTES = Math.min(st.max_bytes || 2 * 1024 * 1024, 2 * 1024 * 1024);
      let sent = 0;
      for (const name of names) {
        const items = cols[name];
        let batch = [], bytes = 0;
        const flush = async () => {
          if (!batch.length) return;
          let ok = false, lastErr = null;
          for (let attempt = 0; attempt < 4 && !ok; attempt++) {
            try {
              await api.post("/admin/restore/batch", { upload_id: uploadId, collection: name, items: batch });
              ok = true;
            } catch (err) {
              lastErr = err;
              if (err.response && err.response.status < 500) break;
              await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
            }
          }
          if (!ok) throw lastErr;
          sent += batch.length; batch = []; bytes = 0;
          setRestoreProg({ pct: Math.round((sent / Math.max(1, total)) * 100), text: `Mengirim data ${name} · ${sent} dari ${total} entri` });
        };
        for (const item of items) {
          const size = JSON.stringify(item).length;
          if (batch.length && bytes + size > MAX_BYTES) await flush();
          batch.push(item); bytes += size;
        }
        await flush();
      }
      setRestoreProg({ pct: 100, processing: true, text: "Mengganti data lama..." });
      const { data: done } = await api.post("/admin/restore/commit", { upload_id: uploadId });
      const count = Object.values(done.restored || {}).reduce((a, b) => a + b, 0);
      setRestoreProg({ pct: 100, text: `Selesai: ${count} entri dipulihkan`, done: true });
      notify(`Data berhasil dipulihkan (${count} entri). Memuat ulang...`);
      window.removeEventListener("beforeunload", warn);
      setTimeout(() => window.location.reload(), 1500);
      return;
    } catch (err) {
      if (uploadId) { try { await api.post("/admin/restore/abort", { upload_id: uploadId }); } catch (e) { /* sesi sudah tidak aktif */ } }
      const status = err.response?.status;
      const msg = status === 413
        ? "Potongan data terlalu besar untuk dikirim. Muat ulang halaman (Ctrl+F5) lalu coba lagi."
        : (err.response?.data?.detail || err.message || "Gagal memulihkan data");
      setRestoreProg({ pct: 0, text: msg, error: true });
      notify(msg);
    } finally {
      window.removeEventListener("beforeunload", warn);
      setBusyData("");
    }
  };

  const [resetOpen, setResetOpen] = useState(false); const [resetPw, setResetPw] = useState(""); const [resetErr, setResetErr] = useState("");
  const openReset = () => { setResetPw(""); setResetErr(""); setResetOpen(true); };
  const reset = async (e) => {
    e.preventDefault();
    if (!resetPw) { setResetErr("Masukkan sandi admin"); return; }
    setBusyData("reset"); setResetErr("");
    try {
      await api.post("/admin/reset-data", { include_books: resetBooks, password: resetPw });
      setResetOpen(false);
      notify("Data berhasil direset. Memuat ulang...");
      setTimeout(() => window.location.reload(), 1200);
    } catch (err) {
      setResetErr(err.response?.data?.detail || "Gagal mereset data");
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
        <p className="account-hint" data-testid="backup-contents-hint"><b>Unduh cadangan</b> menghasilkan satu berkas ZIP: data untuk pemulihan + semua laporan (Excel &amp; PDF) — transaksi, buku masuk, buku hilang, pengunjung, peringkat rajin berkunjung, dan peringkat rajin meminjam per bulan. Keutuhan berkas diperiksa otomatis; bila koneksi terputus, data tetap disimpan sebagai berkas .json yang bisa dipulihkan.</p>
        <div className="data-actions">
          <button type="button" className="secondary" data-testid="backup-data-button" disabled={busyData !== ""} onClick={backup}><Download size={15}/> {busyData === "backup" ? "Menyiapkan cadangan & laporan..." : busyData === "backup-json" ? "Menyimpan data cadangan..." : "Unduh cadangan"}</button>
          <button type="button" className="secondary" data-testid="restore-data-button" disabled={busyData !== ""} onClick={() => restoreRef.current?.click()}><Upload size={15}/> {busyData === "restore" ? "Memulihkan..." : "Pulihkan data"}</button>
          <input ref={restoreRef} type="file" accept="application/json,.json,application/zip,.zip" hidden data-testid="restore-file-input" onChange={pickRestore}/>
        </div>
        {restoreFile && <p className="account-hint" data-testid="restore-file-name">Berkas: <b>{restoreFile.name}</b> ({fmtSize(restoreFile.size)})</p>}
        {restoreProg && <div className={`restore-progress${restoreProg.error ? " error" : ""}${restoreProg.done ? " done" : ""}`} data-testid="restore-progress">
          <div className="restore-progress-track"><div className={restoreProg.processing ? "busy" : ""} style={{ width: `${restoreProg.pct}%` }}/></div>
          <p className="account-hint" data-testid="restore-progress-text">{restoreProg.text}</p>
        </div>}
        <p className="account-hint" data-testid="restore-size-hint">Cadangan berukuran berapa pun bisa dipulihkan. Berkas besar dikirim bertahap — jangan tutup halaman sampai selesai.</p>
        <div className="data-reset-zone">
          <label className="reset-books-check"><input type="checkbox" data-testid="reset-include-books" checked={resetBooks} onChange={e => setResetBooks(e.target.checked)}/> Ikut hapus koleksi buku</label>
          <button type="button" className="danger-btn" data-testid="reset-data-button" disabled={busyData !== ""} onClick={openReset}><Trash2 size={15}/> {busyData === "reset" ? "Mereset..." : "Reset data"}</button>
          <p className="account-hint reset-warn"><AlertTriangle size={13}/> Reset &amp; pulihkan akan mengganti data saat ini dan tidak dapat dibatalkan.</p>
        </div>
      </div>}
    </div>
    {resetOpen && createPortal(<Modal title="Konfirmasi reset data" close={() => busyData !== "reset" && setResetOpen(false)}>
      <form className="modal-form" onSubmit={reset} data-testid="reset-confirm-form">
        <div className="error" data-testid="reset-confirm-warning"><AlertTriangle size={14}/> {resetBooks ? "SEMUA data termasuk koleksi buku" : "Anggota, transaksi, pesanan, pengunjung, dll (kecuali koleksi buku)"} akan dihapus permanen dan tidak dapat dibatalkan.</div>
        <label>Sandi admin<input type="password" autoFocus autoComplete="current-password" data-testid="reset-admin-password-input" value={resetPw} onChange={e => setResetPw(e.target.value)} placeholder="Masukkan sandi akun admin Anda"/></label>
        {resetErr && <div className="error" data-testid="reset-confirm-error">{resetErr}</div>}
        <button type="submit" className="danger-btn full" data-testid="reset-confirm-submit" disabled={busyData === "reset"}><Trash2 size={15}/> {busyData === "reset" ? "Mereset..." : "Ya, reset data"}</button>
        <button type="button" className="secondary full" data-testid="reset-confirm-cancel" disabled={busyData === "reset"} onClick={() => setResetOpen(false)}>Batal</button>
      </form>
    </Modal>, document.body)}
  </Modal>;
}

async function isCompleteZip(blob) {
  // ZIP yang utuh selalu diakhiri tanda "end of central directory" (PK\x05\x06)
  if (!blob || blob.size < 22) return false;
  const tail = new Uint8Array(await blob.slice(Math.max(0, blob.size - 66000)).arrayBuffer());
  for (let i = tail.length - 22; i >= 0; i--) {
    if (tail[i] === 0x50 && tail[i + 1] === 0x4b && tail[i + 2] === 0x05 && tail[i + 3] === 0x06) return true;
  }
  return false;
}

function fmtSize(n) {
  if (!n && n !== 0) return "-";
  if (n >= 1024 * 1024 * 1024) return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
  if (n >= 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(n / 1024))} KB`;
}

