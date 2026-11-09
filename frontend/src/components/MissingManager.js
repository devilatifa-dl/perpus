import { useState } from "react";
import { AlertTriangle, CheckCircle2, RotateCcw, Wallet } from "lucide-react";
import { api } from "../lib";

/**
 * Panel laporan buku hilang: tandai ganti rugi dan pulihkan buku yang ditemukan.
 * Dipakai di tab Laporan > Buku hilang.
 */
export function MissingManager({ rows, reload, notify }) {
  const [busy, setBusy] = useState("");
  const [noteFor, setNoteFor] = useState(null);
  const [note, setNote] = useState("");

  const setCompensation = async (r, compensated) => {
    setBusy(r.id);
    try {
      await api.patch(`/missing/${r.id}/compensation`, { compensated, note: noteFor === r.id ? note : "" });
      notify?.(compensated ? "Ganti rugi ditandai sudah" : "Ganti rugi ditandai belum");
      setNoteFor(null); setNote("");
      reload?.();
    } catch (e) {
      notify?.(e.response?.data?.detail || "Gagal menyimpan ganti rugi");
    } finally { setBusy(""); }
  };

  const markFound = async (r) => {
    setBusy(r.id);
    try {
      await api.patch(`/missing/${r.id}/found`);
      notify?.("Buku dikembalikan ke koleksi");
      reload?.();
    } catch (e) {
      notify?.(e.response?.data?.detail || "Gagal memulihkan buku");
    } finally { setBusy(""); }
  };

  const open = rows.filter((r) => r.status === "Hilang");
  const belum = open.filter((r) => !r.compensated).length;

  return <div className="missing-manager" data-testid="missing-manager">
    <div className="missing-summary">
      <div><AlertTriangle size={16}/><span>Masih hilang</span><b>{open.length}</b></div>
      <div><Wallet size={16}/><span>Belum ganti rugi</span><b>{belum}</b></div>
      <div><CheckCircle2 size={16}/><span>Sudah ganti rugi</span><b>{open.length - belum}</b></div>
    </div>

    {open.length === 0
      ? <p className="muted" data-testid="missing-empty">Tidak ada buku yang masih hilang.</p>
      : <div className="missing-list">
        {open.map((r) => <div className="missing-item" key={r.id} data-testid={`missing-item-${r.id}`}>
          <div className="missing-head">
            <div>
              <b>{r.title}</b>
              <small>{r.code}{r.member_name ? ` · ${r.member_name}` : ""}{r.class_name ? ` (${r.class_name})` : ""}</small>
            </div>
            <span className={`status ${r.compensated ? "ditemukan" : "hilang"}`}>{r.compensated ? "Sudah ganti" : "Belum ganti"}</span>
          </div>
          {r.detail && r.detail !== r.code && <p className="missing-note">{r.detail}</p>}
          {noteFor === r.id && <input className="missing-note-input" data-testid={`missing-note-${r.id}`} placeholder="Catatan ganti rugi (opsional)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={300}/>}
          <div className="missing-actions">
            {r.compensated
              ? <button className="secondary" data-testid={`missing-uncompensate-${r.id}`} disabled={busy === r.id} onClick={() => setCompensation(r, false)}><Wallet size={14}/> Batalkan ganti</button>
              : <button className="primary" data-testid={`missing-compensate-${r.id}`} disabled={busy === r.id} onClick={() => { if (noteFor === r.id) setCompensation(r, true); else { setNoteFor(r.id); setNote(""); } }}><Wallet size={14}/> {noteFor === r.id ? "Simpan ganti rugi" : "Tandai sudah ganti"}</button>}
            <button className="secondary" data-testid={`missing-found-${r.id}`} disabled={busy === r.id} onClick={() => markFound(r)}><RotateCcw size={14}/> Ditemukan</button>
          </div>
        </div>)}
      </div>}
  </div>;
}
