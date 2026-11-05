import { useState } from "react";
import { AlertTriangle, ChevronDown, CloudOff, Database, RefreshCw, RotateCcw, Trash2, Wifi, X } from "lucide-react";
import { useOffline } from "../lib/offline";

const fmtT = (iso) => { if (!iso) return ""; const d = new Date(iso); return Number.isNaN(d.getTime()) ? "" : d.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); };
const KIND = { tx: "Sirkulasi", "visit-scan": "Pengunjung", "visit-guest": "Tamu", "visit-checkout": "Keluar" };

// Indikator status koneksi + antrean data offline (halaman Sirkulasi, Pengunjung, Laporan Pengunjung)
// Petugas bisa membatalkan data yang menunggu, serta mencoba lagi / menghapus data yang ditolak server.
export function OfflineBar({ testId = "offline-bar", kinds }) {
  const { online, queue, syncing, lastSync, rejected, cachedAt, sync, cancelQueued, retryRejected, deleteRejected } = useOffline();
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState(null); // id item / "all" yang menunggu konfirmasi hapus
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState(null);
  const match = (q) => !kinds || kinds.some((k) => q.kind.startsWith(k));
  const mine = queue.filter(match);
  const bad = (rejected || []).filter(match);
  const n = queue.length;
  const sub = online
    ? (syncing ? "Menyinkronkan data offline ke server..." : n ? `${n} data offline menunggu sinkron` : lastSync ? `Semua data tersinkron · ${fmtT(lastSync)}` : "Tersambung ke server · data langsung tersimpan")
    : `Tidak ada internet · data dicatat di perangkat ini${n ? ` · ${n} menunggu sinkron` : ""}`;

  const flash = (text, tone = "info") => { setMsg({ text, tone }); setTimeout(() => setMsg(null), 4500); };
  const askOrRun = async (key, fn) => { if (confirm !== key) { setConfirm(key); return; } setConfirm(null); await fn(); };
  const onCancel = (q) => askOrRun(`q-${q.id}`, async () => { const ok = await cancelQueued(q.id); flash(ok ? "Data offline dibatalkan, tidak akan dikirim ke server" : "Sedang sinkron, coba sebentar lagi"); });
  const onDelete = (q) => askOrRun(`r-${q.id}`, async () => { await deleteRejected(q.id); flash("Data yang ditolak sudah dihapus dari perangkat"); });
  const onDeleteAll = () => askOrRun("all", async () => { await deleteRejected(bad.map((q) => q.id)); flash("Semua data yang ditolak sudah dihapus"); });
  const onRetry = async (q) => {
    setBusy(q.id); setConfirm(null);
    const r = await retryRejected(q.id);
    setBusy(null);
    if (r.ok) flash("Berhasil dikirim ulang dan tersimpan di server", "ok");
    else if (r.net) flash("Belum tersambung ke server, coba lagi saat online", "warn");
    else flash(`Masih ditolak: ${r.reason}`, "bad");
  };
  const showToggle = mine.length > 0 || bad.length > 0;

  return <div className={`offline-bar ${online ? "is-online" : "is-offline"}${syncing ? " is-syncing" : ""}`} data-testid={testId} data-state={online ? "online" : "offline"} role="status" aria-live="polite">
    <div className="ob-main">
      <span className="ob-icon">{online ? <Wifi size={16}/> : <CloudOff size={16}/>}</span>
      <div className="ob-text"><b data-testid={`${testId}-state`}><i className="ob-dot"/>{online ? "Online" : "Offline"}</b><small data-testid={`${testId}-sub`}>{sub}</small></div>
      {!online && cachedAt && <span className="ob-chip" data-testid={`${testId}-cached`}><Database size={12}/> Data tersimpan {fmtT(cachedAt)}</span>}
      {bad.length > 0 && <button type="button" className="ob-chip bad" data-testid={`${testId}-rejected-chip`} onClick={() => setOpen(true)}><AlertTriangle size={12}/> {bad.length} ditolak · perlu dicek</button>}
      <div className="ob-actions">
        {showToggle && <button type="button" className="ob-link" data-testid={`${testId}-toggle`} aria-expanded={open} onClick={() => setOpen((v) => !v)}>{mine.length ? `${mine.length} antre` : "Kelola"} <ChevronDown size={13} className={open ? "rot" : ""}/></button>}
        {n > 0 && <button type="button" className="ob-btn" data-testid={`${testId}-sync`} disabled={!online || syncing} onClick={() => sync()}><RefreshCw size={13} className={syncing ? "spin" : ""}/> {syncing ? "Sinkron..." : "Sinkronkan"}</button>}
      </div>
    </div>
    {open && <div className="ob-list" data-testid={`${testId}-list`}>
      {msg && <p className={`ob-msg ${msg.tone}`} data-testid={`${testId}-msg`}>{msg.text}</p>}
      <div className="ob-section-head"><b>Menunggu sinkron</b><small>{mine.length} data</small></div>
      {mine.map((q) => <div className="ob-item" key={q.id} data-testid={`offline-item-${q.id}`}>
        <em>{KIND[q.kind] || q.kind}</em><span>{q.meta?.label || "-"}</span><time>{fmtT(q.created_at)}</time>
        <div className="ob-item-actions"><button type="button" className={`ob-mini danger${confirm === `q-${q.id}` ? " confirm" : ""}`} data-testid={`offline-cancel-${q.id}`} disabled={syncing} onClick={() => onCancel(q)} title="Batalkan data ini">{confirm === `q-${q.id}` ? "Yakin batalkan?" : <><X size={12}/> Batalkan</>}</button></div>
      </div>)}
      {!mine.length && <p className="ob-empty">Tidak ada data yang menunggu.</p>}
      {bad.length > 0 && <div className="ob-dropped" data-testid={`${testId}-dropped`}>
        <div className="ob-dropped-head"><b><AlertTriangle size={13}/> Ditolak server saat sinkron ({bad.length})</b>
          <button type="button" className={`ob-mini danger${confirm === "all" ? " confirm" : ""}`} data-testid={`${testId}-delete-all`} onClick={onDeleteAll}>{confirm === "all" ? "Yakin hapus semua?" : <><Trash2 size={12}/> Hapus semua</>}</button></div>
        <p className="ob-hint">Periksa alasannya. Setelah masalah diperbaiki (mis. stok sudah kembali), tekan <b>Coba lagi</b>; jika tidak perlu, tekan <b>Hapus</b>.</p>
        {bad.map((q) => <div className="ob-item bad" key={q.id} data-testid={`rejected-item-${q.id}`}>
          <em>{KIND[q.kind] || q.kind}</em>
          <span>{q.meta?.label || "-"} — <i data-testid={`rejected-reason-${q.id}`}>{q.reason}</i><small className="ob-meta">Dicatat {fmtT(q.created_at)} · ditolak {fmtT(q.rejected_at)}{q.attempts > 1 ? ` · ${q.attempts}x dicoba` : ""}</small></span>
          <div className="ob-item-actions">
            <button type="button" className="ob-mini" data-testid={`rejected-retry-${q.id}`} disabled={!online || busy === q.id} onClick={() => onRetry(q)}><RotateCcw size={12} className={busy === q.id ? "spin" : ""}/> {busy === q.id ? "Mengirim..." : "Coba lagi"}</button>
            <button type="button" className={`ob-mini danger${confirm === `r-${q.id}` ? " confirm" : ""}`} data-testid={`rejected-delete-${q.id}`} disabled={busy === q.id} onClick={() => onDelete(q)}>{confirm === `r-${q.id}` ? "Yakin hapus?" : <><Trash2 size={12}/> Hapus</>}</button>
          </div>
        </div>)}
      </div>}
    </div>}
  </div>;
}

export const PendingTag = ({ testId }) => <span className="pending-tag" data-testid={testId} title="Dicatat saat offline, menunggu sinkron"><CloudOff size={11}/> Menunggu sinkron</span>;
