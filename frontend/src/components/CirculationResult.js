import { useEffect } from "react";
import { createPortal } from "react-dom";
import { BookOpen, CheckCircle2, CloudOff, RotateCcw, User, XCircle } from "lucide-react";
import "../Circulation.css";

// Layar hasil transaksi sirkulasi: hijau saat berhasil, merah saat gagal. Hilang sendiri setelah `ms`.
export function CirculationResult({ result, onClose, ms = 2600 }) {
  useEffect(() => {
    if (!result) return undefined;
    const t = setTimeout(onClose, result.ok ? ms : 2200);
    const esc = (e) => { if (e.key === "Escape" || e.key === "Enter") onClose(); };
    window.addEventListener("keydown", esc);
    return () => { clearTimeout(t); window.removeEventListener("keydown", esc); };
  }, [result, onClose, ms]);
  if (!result) return null;
  const borrow = result.mode === "pinjam";
  const status = borrow ? "Dipinjam" : "Dikembalikan";
  return createPortal(<div className={`circ-result ${result.ok ? "ok" : "fail"}`} data-testid="circulation-result" data-result={result.ok ? "success" : "error"} data-mode={result.mode} onClick={onClose} role="status" aria-live="assertive">
    <div className="circ-result-card" onClick={(e) => e.stopPropagation()}>
      <div className="circ-result-icon"><span className="ring"/><span className="ring two"/>{result.ok ? (borrow ? <CheckCircle2 size={56}/> : <RotateCcw size={52}/>) : <XCircle size={56}/>}</div>
      <p className="circ-result-eyebrow">{result.ok ? (borrow ? "PEMINJAMAN BERHASIL" : "PENGEMBALIAN BERHASIL") : (borrow ? "PEMINJAMAN GAGAL" : "PENGEMBALIAN GAGAL")}</p>
      {result.ok ? <>
        <div className="circ-result-row" data-testid="circulation-result-member"><User size={17}/><div><small>Anggota</small><b>{result.member}</b>{result.memberInfo && <em>{result.memberInfo}</em>}</div></div>
        <div className="circ-result-row" data-testid="circulation-result-book"><BookOpen size={17}/><div><small>Judul buku</small><b>{result.book}</b></div></div>
        <span className={`circ-result-status ${borrow ? "borrow" : "return"}`} data-testid="circulation-result-status">{status}</span>
        {result.offline && <p className="circ-result-note" data-testid="circulation-result-offline"><CloudOff size={14}/> Tersimpan di perangkat · disinkronkan otomatis saat online</p>}
      </> : <p className="circ-result-msg" data-testid="circulation-result-message">{result.message}</p>}
      <div className="circ-result-bar"><i style={{ animationDuration: `${result.ok ? ms : 2200}ms` }}/></div>
      <small className="circ-result-hint">Kembali ke sirkulasi otomatis · ketuk untuk menutup</small>
    </div>
  </div>, document.body);
}
