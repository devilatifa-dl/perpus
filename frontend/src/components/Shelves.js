import { BookOpen } from "lucide-react";

export function Shelves({data}) {
  return <div className="shelves-grid">{data.shelves.map(s=>{const books=data.books.filter(b=>b.shelf===s.id);const occ=Math.round((books.length/(s.capacity||1))*100);return <div className="shelf-card" key={s.id} data-testid={`shelf-${s.id}`}><div className="shelf-head"><div><p className="eyebrow">RAK {s.id}</p><h3>{s.name}</h3></div><span className="shelf-tag">{books.length}/{s.capacity}</span></div><div className="shelf-bar"><div style={{width:`${Math.min(occ,100)}%`}}/></div><small>{occ}% kapasitas</small><div className="shelf-books">{books.slice(0,6).map(b=><div className="shelf-spine" key={b.id} title={b.title}>{b.cover?<img src={b.cover} alt={b.title}/>:<BookOpen size={14}/>}<span>{b.title}</span></div>)}{books.length===0&&<p className="muted" style={{fontSize:12}}>Belum ada buku di rak ini</p>}</div></div>})}</div>
}
