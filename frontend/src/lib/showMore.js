import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { ChevronDown } from "lucide-react";
import "../LoadMore.css";

// Tampilkan daftar bertahap (lazy): baris berikutnya dimuat otomatis saat digulir. Saat mencetak, semua baris tampil.
export function useShowMore(items, step = 50) {
  const total = items?.length || 0;
  const [limit, setLimit] = useState(step);
  const [printing, setPrinting] = useState(false);
  const ref = useRef(null);
  useEffect(() => { setLimit(step); }, [total, step]);
  useEffect(() => {
    const on = () => flushSync(() => setPrinting(true));
    const off = () => setPrinting(false);
    window.addEventListener("beforeprint", on); window.addEventListener("afterprint", off);
    return () => { window.removeEventListener("beforeprint", on); window.removeEventListener("afterprint", off); };
  }, []);
  useEffect(() => {
    const el = ref.current;
    if (!el || limit >= total || typeof IntersectionObserver === "undefined") return undefined;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) setLimit((l) => l + step); }, { rootMargin: "400px" });
    io.observe(el);
    return () => io.disconnect();
  }, [limit, total, step]);
  const visible = printing ? (items || []) : (items || []).slice(0, limit);
  return { visible, total, hasMore: !printing && limit < total, more: () => setLimit((l) => l + step), ref };
}

export function ShowMore({ items, step = 50, colSpan, children }) {
  const s = useShowMore(items, step);
  const btn = <button type="button" className="load-more-btn" data-testid="load-more-button" onClick={s.more}><ChevronDown size={15}/> Muat lebih banyak <small>({s.visible.length} dari {s.total})</small></button>;
  return <>
    {children(s.visible)}
    {s.hasMore && (colSpan
      ? <tr className="load-more-row print-hide" ref={s.ref}><td colSpan={colSpan}>{btn}</td></tr>
      : <div className="load-more-row print-hide" ref={s.ref}>{btn}</div>)}
  </>;
}
