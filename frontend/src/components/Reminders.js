import { useState } from "react";
import { BellRing, BookOpen, Check, Clock, X } from "lucide-react";
import { api, fmtDate } from "../lib";

export function OverduePanel({ overdue, onNavigate }) {
  const items = overdue?.items || [];
  return <div className="panel overdue-panel" data-testid="overdue-panel">
    <div className="panel-title"><div><p className="eyebrow">PENGINGAT KEMBALI</p><h3>Dipinjam lebih dari {overdue?.days || 7} hari</h3></div><span className={items.length ? "soft-badge warn" : "soft-badge"}><BellRing size={14}/> {items.length} buku</span></div>
    {items.length === 0 && <p className="muted" data-testid="overdue-empty">Semua peminjaman masih dalam batas waktu. Kerja bagus!</p>}
    {items.slice(0, 6).map((l) => <div className="overdue-row" key={l.id} data-testid={`overdue-${l.id}`}>
      <div className="activity-icon overdue"><Clock size={15}/></div>
      <div><b>{l.member_name}</b><span>“{l.book_title}” · {l.book_id} · sejak {fmtDate(l.borrowed_at)}</span></div>
      <span className="days-pill" data-testid={`overdue-days-${l.id}`}>{l.days_out} hari</span>
    </div>)}
    {items.length > 0 && <button className="text-button" data-testid="overdue-goto-circulation" onClick={() => onNavigate("circulation")}>Proses pengembalian →</button>}
  </div>;
}

export function ReservationQueue({ reservations, reload, notify }) {
  const [busy, setBusy] = useState("");
  const waiting = (reservations || []).filter((r) => r.status === "Menunggu");
  const done = (reservations || []).filter((r) => r.status !== "Menunggu").slice(0, 4);
  const act = async (r, action) => {
    setBusy(r.id);
    try { await api.post(`/reservations/${r.id}/process`, { action }); reload(); notify(action === "pinjam" ? `“${r.book_title}” dipinjamkan ke ${r.member_name}` : "Pesanan ditolak"); }
    catch (e) { notify(e.response?.data?.detail || "Gagal memproses"); }
    finally { setBusy(""); }
  };
  return <div className="panel queue-panel" data-testid="reservation-queue">
    <div className="panel-title"><div><p className="eyebrow">ANTREAN PESANAN SISWA</p><h3>{waiting.length} menunggu diproses</h3></div></div>
    {waiting.length === 0 && <p className="muted" data-testid="queue-empty">Belum ada pesanan dari portal siswa.</p>}
    {waiting.map((r) => <div className="queue-row" key={r.id} data-testid={`reservation-${r.id}`}>
      <div className="activity-icon borrow"><BookOpen size={15}/></div>
      <div><b>{r.member_name} <small>· {r.class_name}</small></b><span>“{r.book_title}” · Rak {r.book_shelf} · {fmtDate(r.created_at)}</span></div>
      <div className="queue-actions">
        <button className="ok-icon" title="Pinjamkan" data-testid={`approve-${r.id}`} disabled={busy === r.id} onClick={() => act(r, "pinjam")}><Check size={15}/></button>
        <button className="danger-icon" title="Tolak" data-testid={`reject-${r.id}`} disabled={busy === r.id} onClick={() => act(r, "tolak")}><X size={15}/></button>
      </div>
    </div>)}
    {done.length > 0 && <div className="queue-done"><p className="eyebrow">TERAKHIR DIPROSES</p>{done.map((r) => <div className="queue-row muted-row" key={r.id}><div><b>{r.member_name}</b><span>“{r.book_title}”</span></div><span className={`status ${r.status === "Dipinjamkan" ? "dipinjam" : r.status === "Ditolak" ? "hilang" : "tersedia"}`}>{r.status}</span></div>)}</div>}
  </div>;
}
