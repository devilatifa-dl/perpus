import { useEffect, useState } from "react";
import { BookOpen, History } from "lucide-react";
import { api, fmtDate } from "../lib";

export function MemberHistory({ member, refreshKey }) {
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    if (!member) return;
    let alive = true; setState({ loading: true });
    api.get(`/members/${member.id}/history`).then((r) => alive && setState({ data: r.data })).catch((e) => alive && setState({ error: e.response?.data?.detail || "Riwayat tidak dapat dimuat" }));
    return () => { alive = false; };
  }, [member?.id, refreshKey]);
  if (!member) return null;
  const d = state.data;
  return <div className="panel history-panel" data-testid="member-history-panel">
    <div className="panel-title"><div><p className="eyebrow">RIWAYAT PEMINJAMAN</p><h3>{member.name.split(" ")[0]} pernah meminjam</h3></div>{d && <span className="soft-badge"><History size={14}/> {d.total} buku · {d.active} aktif</span>}</div>
    {state.loading && <p className="muted" data-testid="history-loading">Memuat riwayat...</p>}
    {state.error && <div className="error" data-testid="history-error">{state.error}</div>}
    {d && d.history.length === 0 && <p className="muted" data-testid="history-empty">Belum pernah meminjam buku.</p>}
    {d && d.history.map((h) => <div className="history-row" key={h.id} data-testid={`history-${h.id}`}>
      <div className={`activity-icon ${h.returned ? "return" : "borrow"}`}><BookOpen size={15}/></div>
      <div><b>{h.book_title}</b><span>{h.book_id} · dipinjam {fmtDate(h.date)}{h.returned ? ` · kembali ${fmtDate(h.returned_at)}` : ""}</span></div>
      <span className={`status ${h.returned ? "tersedia" : "dipinjam"}`}>{h.returned ? "Dikembalikan" : "Dipinjam"}</span>
    </div>)}
  </div>;
}
