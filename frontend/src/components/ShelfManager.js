import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";
import { Shelves } from "./Shelves";

const COLORS = [["azure", "Biru"], ["mint", "Hijau"], ["amber", "Kuning"], ["rose", "Merah muda"], ["violet", "Ungu"]];

export function ShelfManager({ data, user, reload, notify }) {
  const staff = user.role !== "siswa";
  const [form, setForm] = useState(null); const [editing, setEditing] = useState(null); const [err, setErr] = useState("");
  const [del, setDel] = useState(null); const [moveTo, setMoveTo] = useState(""); const [busy, setBusy] = useState(false);
  const nextCode = () => { const nums = data.shelves.map((s) => parseInt(String(s.id).replace(/\D/g, ""), 10)).filter((n) => !isNaN(n)); return `R-${String((nums.length ? Math.max(...nums) : 0) + 1).padStart(2, "0")}`; };
  const openAdd = () => { setEditing(null); setErr(""); setForm({ id: nextCode(), name: "", capacity: 50, color: "azure" }); };
  const openEdit = (s) => { setEditing(s); setErr(""); setForm({ id: s.id, name: s.name, capacity: s.capacity, color: s.color || "azure" }); };
  const openDelete = (s) => { setDel(s); setErr(""); setMoveTo(data.shelves.find((x) => x.id !== s.id)?.id || ""); };
  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const body = { ...form, id: form.id.trim().toUpperCase(), capacity: Number(form.capacity) };
      if (editing) { const { data: r } = await api.put(`/shelves/${editing.id}`, body); notify(r.books_updated ? `Rak ${r.id} diperbarui · ${r.books_updated} judul ikut pindah kode` : `Rak ${r.id} diperbarui`); }
      else { const { data: r } = await api.post("/shelves", body); notify(`Rak ${r.id} ditambahkan`); }
      setForm(null); setEditing(null); reload();
    } catch (e2) { const d = e2.response?.data?.detail; setErr(Array.isArray(d) ? "Periksa isian: kode rak hanya huruf, angka, dan tanda minus" : d || "Gagal menyimpan rak"); }
    finally { setBusy(false); }
  };
  const remove = async () => {
    setErr(""); setBusy(true);
    try { const { data: r } = await api.delete(`/shelves/${del.id}`, { params: r_count(del) ? { move_to: moveTo } : {} }); notify(r.moved ? `Rak ${del.id} dihapus · ${r.moved} judul dipindah ke ${r.move_to}` : `Rak ${del.id} dihapus`); setDel(null); reload(); }
    catch (e2) { setErr(e2.response?.data?.detail || "Gagal menghapus rak"); }
    finally { setBusy(false); }
  };
  const r_count = (s) => data.books.filter((b) => b.shelf === s.id).length;
  return <>
    {staff && <div className="shelf-admin-bar"><div><b>{data.shelves.length} rak</b><span> · kelola nama, kode, dan kapasitas rak</span></div><button className="secondary" data-testid="add-shelf-button" onClick={openAdd}><Plus size={16}/> Tambah rak</button></div>}
    <Shelves data={data} onEdit={staff ? openEdit : null} onDelete={staff ? openDelete : null}/>
    {form && <Modal title={editing ? `Edit rak ${editing.id}` : "Tambah rak"} close={() => setForm(null)}><form className="modal-form" onSubmit={save} data-testid="shelf-form">
      <label>Kode rak<input data-testid="shelf-code-input" required maxLength={12} value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })}/></label>
      {editing && form.id.trim().toUpperCase() !== editing.id && <p className="muted" style={{ fontSize: 11, marginTop: -6 }}>Semua buku di rak {editing.id} otomatis pindah ke kode baru.</p>}
      <label>Nama rak<input data-testid="shelf-name-input" required maxLength={60} placeholder="mis. Agama & Budaya" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}/></label>
      <label>Kapasitas (eksemplar)<input data-testid="shelf-capacity-input" type="number" min={1} max={10000} required value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })}/></label>
      <label>Warna label<select data-testid="shelf-color-input" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })}>{COLORS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
      {err && <div className="error" data-testid="shelf-error">{err}</div>}
      <button className="primary full" data-testid="save-shelf-button" disabled={busy}>{busy ? "Menyimpan..." : editing ? "Simpan perubahan" : "Tambah rak"}</button>
    </form></Modal>}
    {del && <Modal title={`Hapus rak ${del.id}`} close={() => setDel(null)}><div className="modal-form" data-testid="delete-shelf-modal">
      <div className="lost-banner warn"><Trash2 size={20}/><div><b>{del.name}</b><small>Rak {del.id} · {r_count(del)} judul buku</small></div></div>
      {r_count(del) > 0 ? <label>Pindahkan {r_count(del)} judul buku ke rak<select data-testid="shelf-move-select" value={moveTo} onChange={(e) => setMoveTo(e.target.value)}>{data.shelves.filter((x) => x.id !== del.id).map((x) => <option key={x.id} value={x.id}>{x.id} · {x.name}</option>)}</select></label> : <p className="muted" style={{ fontSize: 13 }}>Rak ini kosong dan aman untuk dihapus.</p>}
      {err && <div className="error" data-testid="shelf-error">{err}</div>}
      <button className="danger full" data-testid="confirm-delete-shelf-button" disabled={busy || (r_count(del) > 0 && !moveTo)} onClick={remove}>{busy ? "Menghapus..." : r_count(del) > 0 ? "Pindahkan buku & hapus rak" : "Hapus rak"}</button>
    </div></Modal>}
  </>;
}
