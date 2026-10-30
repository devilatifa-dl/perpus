import { useEffect } from "react";
import { X } from "lucide-react";

export function CoverZoom({ book, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [onClose]);
  return <div className="cover-zoom" data-testid="cover-zoom-overlay" onClick={onClose} role="dialog" aria-label={`Sampul ${book.title}`}>
    <button type="button" className="cover-zoom-close" data-testid="cover-zoom-close" onClick={onClose} aria-label="Tutup"><X size={22}/></button>
    <img src={book.cover} alt={book.title} data-testid="cover-zoom-image" onClick={(e) => e.stopPropagation()}/>
    <div className="cover-zoom-caption"><b>{book.title}</b>{book.author && <small>{book.author}</small>}</div>
  </div>;
}
