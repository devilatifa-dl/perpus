import { useMemo, useState } from "react";
import { Search, X } from "lucide-react";

export function MemberSearch({ members, value, onChange }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const selected = members.find((m) => m.id === value);
  const results = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return [];
    return members.filter((m) => [m.name, m.student_id, m.class_name].some((v) => (v || "").toLowerCase().includes(t))).slice(0, 8);
  }, [q, members]);
  const pick = (m) => { onChange(m.id); setQ(""); setOpen(false); setHi(0); };
  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(h + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
    else if (e.key === "Enter" && results[hi]) { e.preventDefault(); pick(results[hi]); }
    else if (e.key === "Escape") setOpen(false);
  };

  if (selected) return <div className="member-picked" data-testid="circulation-member-selected">
    <div className="avatar">{selected.name[0]}</div>
    <div><b>{selected.name}</b><small>{selected.student_id || "-"} · {selected.class_name}</small></div>
    <button type="button" className="icon-button" data-testid="circulation-member-clear" onClick={() => onChange("")} aria-label="Ganti anggota"><X size={16}/></button>
  </div>;

  return <div className="member-search">
    <div className="searchbox"><Search size={16}/><input data-testid="circulation-member-search" placeholder="Ketik nama, NIS, atau kelas..." value={q}
      onChange={(e) => { setQ(e.target.value); setOpen(true); setHi(0); }} onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)} onKeyDown={onKey}/></div>
    {open && q.trim() && <div className="member-results" data-testid="circulation-member-results">
      {results.length === 0 ? <div className="member-empty">Anggota tidak ditemukan</div> :
        results.map((m, i) => <button type="button" key={m.id} className={i === hi ? "active" : ""} data-testid={`circulation-member-option-${m.id}`} onMouseDown={(e) => { e.preventDefault(); pick(m); }} onMouseEnter={() => setHi(i)}>
          <div className="avatar">{m.name[0]}</div><div><b>{m.name}</b><small>{m.student_id || "-"} · {m.class_name}</small></div>
        </button>)}
    </div>}
  </div>;
}
