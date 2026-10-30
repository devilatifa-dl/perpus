import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { QRCodeSVG } from "qrcode.react";
import { CheckSquare, Printer, Search, Square, X } from "lucide-react";

const PER_PAGE = 24; // 4 kolom x 6 baris di kertas A4

function Label({ book, showCode }) {
  return <div className="qrb-label" data-testid={`qr-label-${book.id}`}>
    <QRCodeSVG value={book.id} size={256} level="M" marginSize={0} fgColor="#0f2745" bgColor="#ffffff" className="qrb-qr"/>
    <b className="qrb-title">{book.title}</b>
    <small className="qrb-meta">{showCode ? `${book.id} · ` : ""}Rak {book.shelf || "-"}</small>
  </div>;
}

export function BulkBookQrPrint({ books, shelves = [], close, initialIds = null, initialCopies = "satu" }) {
  const [scope, setScope] = useState(initialIds ? "pilih" : "semua");
  const [shelf, setShelf] = useState("semua");
  const [copies, setCopies] = useState(initialCopies);
  const [showCode, setShowCode] = useState(true);
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState(() => new Set(initialIds || []));

  useEffect(() => { document.body.classList.add("bulk-mode"); return () => document.body.classList.remove("bulk-mode"); }, []);
  useEffect(() => { const onKey = (e) => e.key === "Escape" && close(); window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey); }, [close]);

  const sorted = useMemo(() => [...books].sort((a, b) => (a.shelf || "").localeCompare(b.shelf || "", "id", { numeric: true }) || a.title.localeCompare(b.title, "id")), [books]);
  const inShelf = useMemo(() => sorted.filter((b) => shelf === "semua" || b.shelf === shelf), [sorted, shelf]);
  const visible = useMemo(() => {
    const t = q.trim().toLowerCase();
    return t ? inShelf.filter((b) => [b.title, b.author, b.id, b.category].some((v) => (v || "").toLowerCase().includes(t))) : inShelf;
  }, [inShelf, q]);
  const chosen = scope === "semua" ? inShelf : sorted.filter((b) => picked.has(b.id));
  const labels = useMemo(() => chosen.flatMap((b) => Array.from({ length: copies === "stok" ? Math.max(1, Number(b.stock) || 1) : 1 }, (_, i) => ({ book: b, key: `${b.id}-${i}` }))), [chosen, copies]);
  const pages = Array.from({ length: Math.ceil(labels.length / PER_PAGE) }, (_, i) => labels.slice(i * PER_PAGE, (i + 1) * PER_PAGE));

  const toggle = (id) => setPicked((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const pickVisible = () => setPicked((s) => { const n = new Set(s); visible.forEach((b) => n.add(b.id)); return n; });
  const allVisiblePicked = visible.length > 0 && visible.every((b) => picked.has(b.id));

  return createPortal(<div className="bulk-print qrb" data-testid="bulk-qr-view">
    <div className="bulk-toolbar">
      <div><p className="eyebrow">CETAK MASSAL QR BUKU</p><h3 data-testid="bulk-qr-summary">{chosen.length} judul · {labels.length} label · {pages.length} halaman A4</h3></div>
      <div className="bulk-actions">
        <button className="primary" data-testid="bulk-qr-print-button" onClick={() => window.print()} disabled={!labels.length}><Printer size={16}/> Cetak {labels.length} label</button>
        <button className="icon-button" data-testid="bulk-qr-close-button" onClick={close} aria-label="Tutup"><X size={18}/></button>
      </div>
    </div>

    <div className="qrb-controls" data-testid="bulk-qr-controls">
      <div className="qrb-row">
        <div className="qrb-seg" role="radiogroup" aria-label="Buku yang dicetak">
          <button type="button" role="radio" aria-checked={scope === "semua"} className={scope === "semua" ? "active" : ""} data-testid="bulk-qr-scope-all" onClick={() => setScope("semua")}>Semua buku</button>
          <button type="button" role="radio" aria-checked={scope === "pilih"} className={scope === "pilih" ? "active" : ""} data-testid="bulk-qr-scope-pick" onClick={() => setScope("pilih")}>Pilih per buku</button>
        </div>
        <label className="qrb-field">Rak<select data-testid="bulk-qr-shelf-select" value={shelf} onChange={(e) => setShelf(e.target.value)}><option value="semua">Semua rak</option>{shelves.map((s) => <option key={s.id} value={s.id}>{s.id} · {s.name}</option>)}</select></label>
        <label className="qrb-field">Jumlah label<select data-testid="bulk-qr-copies-select" value={copies} onChange={(e) => setCopies(e.target.value)}><option value="satu">1 label per judul</option><option value="stok">Sesuai jumlah eksemplar</option></select></label>
        <label className="qrb-check"><input type="checkbox" data-testid="bulk-qr-show-code" checked={showCode} onChange={(e) => setShowCode(e.target.checked)}/> Tampilkan kode buku</label>
      </div>

      {scope === "pilih" && <div className="qrb-picker" data-testid="bulk-qr-picker">
        <div className="qrb-picker-head">
          <div className="searchbox"><Search size={16}/><input data-testid="bulk-qr-search" placeholder="Cari judul, penulis, kode..." value={q} onChange={(e) => setQ(e.target.value)}/></div>
          <button type="button" className="secondary" data-testid="bulk-qr-pick-visible" onClick={pickVisible} disabled={!visible.length || allVisiblePicked}><CheckSquare size={15}/> Pilih semua yang tampil</button>
          <button type="button" className="secondary" data-testid="bulk-qr-clear" onClick={() => setPicked(new Set())} disabled={!picked.size}>Kosongkan ({picked.size})</button>
        </div>
        <div className="qrb-list">
          {visible.map((b) => { const on = picked.has(b.id); return <button type="button" key={b.id} className={`qrb-item${on ? " on" : ""}`} aria-pressed={on} data-testid={`bulk-qr-pick-${b.id}`} onClick={() => toggle(b.id)}>
            {on ? <CheckSquare size={17}/> : <Square size={17}/>}
            <span className="qrb-item-text"><b>{b.title}</b><small>{b.author || "-"} · {b.id} · Rak {b.shelf || "-"} · {b.stock || 0} eks</small></span>
          </button>; })}
          {visible.length === 0 && <p className="muted qrb-empty">Buku tidak ditemukan.</p>}
        </div>
      </div>}
      <p className="bulk-hint" data-testid="bulk-qr-hint">Label 4 × 6 per halaman A4. Di dialog cetak pilih ukuran A4, skala 100%, margin tidak ada. Gunting mengikuti garis putus-putus.</p>
    </div>

    {labels.length === 0
      ? <p className="muted qrb-none" data-testid="bulk-qr-empty">{scope === "pilih" ? "Belum ada buku yang dipilih. Centang buku di daftar di atas." : "Tidak ada buku di rak ini."}</p>
      : pages.map((pg, i) => <div className="qrb-sheet" key={i} data-testid={`bulk-qr-sheet-${i + 1}`}>{pg.map((l) => <Label key={l.key} book={l.book} showCode={showCode}/>)}</div>)}
  </div>, document.body);
}
