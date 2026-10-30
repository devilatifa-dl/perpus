import { useMemo, useState } from "react";
import { BookOpen, Search, X } from "lucide-react";

const Thumb = ({ b }) => <div className="avatar book-thumb">{b.cover ? <img src={b.cover} alt=""/> : <BookOpen size={15}/>}</div>;
const info = (b) => `${b.id} · stok ${b.available}/${b.stock}${b.author ? ` · ${b.author}` : ""}`;

export function BookSearch({ books, value, onChange, selectedBook, emptyText }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const results = useMemo(() => {
    const t = q.trim().toLowerCase();
    const list = t ? books.filter((b) => [b.title, b.id, b.author, b.isbn, b.category].some((v) => (v || "").toLowerCase().includes(t))) : books;
    return list.slice(0, 8);
  }, [q, books]);
  const pick = (b) => { onChange(b.id); setQ(""); setOpen(false); setHi(0); };
  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(h + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
    else if (e.key === "Enter" && results[hi]) { e.preventDefault(); pick(results[hi]); }
    else if (e.key === "Escape") setOpen(false);
  };

  if (value && selectedBook) return <div className="member-picked" data-testid="circulation-book-selected">
    <Thumb b={selectedBook}/>
    <div><b>{selectedBook.title}</b><small>{info(selectedBook)}</small></div>
    <button type="button" className="icon-button" data-testid="circulation-book-clear" onClick={() => onChange("")} aria-label="Ganti buku"><X size={16}/></button>
  </div>;

  return <div className="member-search">
    <div className="searchbox"><Search size={16}/><input data-testid="circulation-book-search" placeholder="Ketik judul, kode, atau penulis buku..." value={q}
      onChange={(e) => { setQ(e.target.value); setOpen(true); setHi(0); }} onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)} onKeyDown={onKey}/></div>
    {open && <div className="member-results" data-testid="circulation-book-results">
      {results.length === 0 ? <div className="member-empty">{q.trim() ? "Buku tidak ditemukan" : emptyText}</div> :
        results.map((b, i) => <button type="button" key={b.id} className={i === hi ? "active" : ""} data-testid={`circulation-book-option-${b.id}`} onMouseDown={(e) => { e.preventDefault(); pick(b); }} onMouseEnter={() => setHi(i)}>
          <Thumb b={b}/><div><b>{b.title}</b><small>{info(b)}</small></div>
        </button>)}
    </div>}
  </div>;
}
