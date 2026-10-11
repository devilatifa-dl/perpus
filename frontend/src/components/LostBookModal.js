import { useState } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

export function LostBookModal({ book, user, mode, close, onDone }) {
  const lost = mode === "lost";
  const [note, setNote] = useState(""); const [reporter, setReporter] = useState(user.name); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError("");
    try { await api.patch(`/books/${book.id}/status`, lost ? { status: "Hilang", note, reporter } : { status: "Tersedia" }); onDone(); close(); }
    catch (err) { setError(err.response?.data?.detail || "Gagal menyimpan"); }
    finally { setBusy(false); }
  };
  return <Modal title={lost ? "Lapor buku hilang" : "Buku ditemukan kembali"} close={close}>
    <form onSubmit={submit} className="modal-form" data-testid={lost ? "lost-book-form" : "found-book-form"}>
      <div className={`lost-banner ${lost ? "warn" : "ok"}`}>{lost ? <AlertTriangle size={20}/> : <RotateCcw size={20}/>}<div><b>{book.title}</b><small>{book.author} · {book.id} · Rak {book.shelf}</small></div></div>
      {lost ? <>
        <label>Catatan kehilangan<textarea data-testid="lost-note-input" rows={3} placeholder="Contoh: tidak ditemukan saat stock opname, terakhir dipinjam kelas XI IPA 2" value={note} onChange={(e) => setNote(e.target.value)}/></label>
        <label>Nama pelapor<input data-testid="lost-reporter-input" required value={reporter} onChange={(e) => setReporter(e.target.value)}/></label>
        <p className="muted" style={{ fontSize: 12 }}>Buku tetap tercatat di koleksi dengan status <b>Hilang</b> dan masuk laporan buku hilang. Bisa dipulihkan jika ditemukan.</p>
      </> : <p className="muted" style={{ fontSize: 13 }}>Status buku akan kembali <b>Tersedia</b> dan laporan kehilangannya ditandai <b>Ditemukan</b>.</p>}
      {error && <div className="error" data-testid="lost-error">{error}</div>}
      <button className={lost ? "primary full warn-btn" : "primary full"} data-testid="confirm-status-button" disabled={busy}>{busy ? "Menyimpan..." : lost ? "Tandai hilang" : "Pulihkan ke koleksi"}</button>
    </form>
  </Modal>;
}
