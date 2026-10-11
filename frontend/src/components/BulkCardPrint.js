import { useEffect, useMemo, useState } from "react";
import { Printer, X } from "lucide-react";
import { MemberCard } from "./MemberCard";

export function BulkCardPrint({ members, settings, close }) {
  const classes = useMemo(() => [...new Set(members.map((m) => m.class_name))].sort(), [members]);
  const [klass, setKlass] = useState("semua");
  const list = members.filter((m) => klass === "semua" || m.class_name === klass);
  const portrait = settings?.card_layout === "portrait";
  const perPage = portrait ? 8 : 10;
  useEffect(() => { document.body.classList.add("bulk-mode"); return () => document.body.classList.remove("bulk-mode"); }, []);
  return <div className="bulk-print" data-testid="bulk-print-view">
    <div className="bulk-toolbar">
      <div><p className="eyebrow">CETAK MASSAL KARTU ANGGOTA</p><h3>{list.length} kartu · {Math.ceil(list.length / perPage) || 0} halaman A4 · ukuran ID 85,6 × 54 mm</h3></div>
      <div className="bulk-actions">
        <label>Kelas<select data-testid="bulk-class-select" value={klass} onChange={(e) => setKlass(e.target.value)}><option value="semua">Semua kelas</option>{classes.map((c) => <option key={c} value={c}>{c}</option>)}</select></label>
        <button className="primary" data-testid="bulk-print-button" onClick={() => window.print()} disabled={!list.length}><Printer size={16}/> Cetak {list.length} kartu</button>
        <button className="icon-button" data-testid="bulk-close-button" onClick={close}><X size={18}/></button>
      </div>
    </div>
    <div className={`print-sheet ${portrait ? "portrait" : ""}`} data-testid="print-sheet">
      {list.map((m) => <div className="print-slot" key={m.id} data-testid={`bulk-card-${m.id}`}><MemberCard member={m} settings={settings}/></div>)}
      {list.length === 0 && <p className="muted">Tidak ada anggota di kelas ini.</p>}
    </div>
  </div>;
}
