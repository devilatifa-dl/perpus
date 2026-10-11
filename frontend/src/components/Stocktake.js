import { useState } from "react";
import { AlertTriangle, Check, ClipboardCheck, QrCode, ScanLine, X } from "lucide-react";
import { api } from "../lib";
import { QRScanner } from "./QRScanner";
import { LostBookModal } from "./LostBookModal";

export function Stocktake({ data, user, reload, notify, close }) {
  const [shelf, setShelf] = useState(data.shelves[0]?.id || "");
  const [scanned, setScanned] = useState([]); const [misplaced, setMisplaced] = useState([]);
  const [manual, setManual] = useState(""); const [scan, setScan] = useState(false); const [finished, setFinished] = useState(false); const [lostTarget, setLostTarget] = useState(null); const [saved, setSaved] = useState(null);
  const shelfBooks = data.books.filter((b) => b.shelf === shelf && b.status !== "Hilang");
  const unscanned = shelfBooks.filter((b) => !scanned.includes(b.id));
  const handle = (code) => {
    const c = code.trim().toUpperCase(); const book = data.books.find((b) => b.id.toUpperCase() === c || (b.isbn && b.isbn.toUpperCase() === c));
    if (!book) return notify("Kode buku tidak dikenal: " + c);
    if (book.shelf !== shelf) { if (!misplaced.find((m) => m.id === book.id)) setMisplaced([...misplaced, book]); return notify(`“${book.title}” seharusnya di rak ${book.shelf}`); }
    if (scanned.includes(book.id)) return notify("Sudah dipindai");
    setScanned([...scanned, book.id]); notify(`✓ ${book.title}`);
  };
  const finish = async () => {
    setFinished(true);
    const { data: res } = await api.post("/stocktake", { shelf, scanned, unscanned: unscanned.map((b) => b.id), misplaced: misplaced.map((b) => b.id) });
    setSaved(res); reload();
  };
  const restart = () => { setScanned([]); setMisplaced([]); setFinished(false); setSaved(null); };
  const pct = shelfBooks.length ? Math.round((scanned.length / shelfBooks.length) * 100) : 0;
  return <div className="panel stocktake" data-testid="stocktake-panel">
    <div className="panel-title"><div><p className="eyebrow">STOK OPNAME</p><h3>Pemeriksaan fisik rak</h3></div><button className="icon-button" data-testid="stocktake-close-button" onClick={close}><X size={18}/></button></div>
    <div className="stock-head">
      <label>Rak yang diperiksa<select data-testid="stocktake-shelf-select" value={shelf} disabled={scanned.length > 0} onChange={(e) => { setShelf(e.target.value); restart(); }}>{data.shelves.map((s) => <option key={s.id} value={s.id}>{s.id} · {s.name}</option>)}</select></label>
      <div className="stock-progress"><div className="stock-numbers"><b data-testid="stocktake-progress">{scanned.length}/{shelfBooks.length}</b><span>buku terpindai · {pct}%</span></div><div className="shelf-bar"><div style={{ width: `${pct}%` }}/></div></div>
    </div>
    {!finished && <>
      <div className="scan-buttons"><button className="primary" data-testid="stocktake-scan-button" onClick={() => setScan(true)}><QrCode size={16}/> Pindai QR buku</button></div>
      <div className="manual-row"><input placeholder="Atau ketik kode buku (BK-xxx) lalu Enter" value={manual} data-testid="stocktake-manual-input" onChange={(e) => setManual(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handle(manual); setManual(""); } }}/><button className="secondary" data-testid="stocktake-apply-button" onClick={() => { handle(manual); setManual(""); }}>Tandai</button></div>
    </>}
    <div className="stock-grid">
      <div><p className="eyebrow">DAFTAR BUKU DI RAK {shelf}</p>
        {shelfBooks.map((b) => { const ok = scanned.includes(b.id); return <div className={ok ? "stock-row ok" : "stock-row"} key={b.id} data-testid={`stock-${b.id}`}>
          <span className={ok ? "tick on" : "tick"}>{ok ? <Check size={13}/> : null}</span>
          <div><b>{b.title}</b><span>{b.id} · {b.author}</span></div>
          {!finished && !ok && <button className="text-button" data-testid={`stock-mark-${b.id}`} onClick={() => handle(b.id)}>Ada</button>}
          {finished && !ok && <button className="warn-icon" title="Tandai hilang" data-testid={`stock-lost-${b.id}`} onClick={() => setLostTarget(b)}><AlertTriangle size={15}/></button>}
          {finished && !ok && <span className="status hilang">Tidak terpindai</span>}
        </div>; })}
        {shelfBooks.length === 0 && <p className="muted">Rak ini kosong.</p>}
      </div>
      <div>
        <p className="eyebrow">SALAH RAK ({misplaced.length})</p>
        {misplaced.length === 0 && <p className="muted" style={{ fontSize: 12 }}>Belum ada buku dari rak lain yang terpindai di sini.</p>}
        {misplaced.map((b) => <div className="stock-row warn" key={b.id} data-testid={`misplaced-${b.id}`}><span className="tick warn"><AlertTriangle size={12}/></span><div><b>{b.title}</b><span>{b.id} · seharusnya rak {b.shelf}</span></div></div>)}
        {finished && saved && <div className="stock-summary" data-testid="stocktake-summary"><ClipboardCheck size={18}/><div><b>Hasil tersimpan ({saved.id})</b><span>{saved.scanned_count} ada · {saved.unscanned_count} tidak terpindai · {saved.misplaced_count} salah rak</span></div></div>}
      </div>
    </div>
    <div className="stock-foot">
      {!finished ? <button className="primary" data-testid="stocktake-finish-button" onClick={finish} disabled={shelfBooks.length === 0}><ScanLine size={16}/> Selesai & simpan hasil</button>
        : <button className="secondary" data-testid="stocktake-restart-button" onClick={restart}>Periksa rak lain</button>}
    </div>
    {scan && <QRScanner onDetect={(code) => { setScan(false); handle(code); }} onClose={() => setScan(false)}/>}
    {lostTarget && <LostBookModal book={lostTarget} mode="lost" user={user} close={() => setLostTarget(null)} onDone={() => { reload(); notify("Buku ditandai hilang"); }}/>}
  </div>;
}
