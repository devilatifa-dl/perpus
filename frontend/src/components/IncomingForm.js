import { useState } from "react";
import { PackagePlus } from "lucide-react";
import { api } from "../lib";
import { Modal, PhotoBox } from "./Shared";

const today = () => new Date().toISOString().slice(0, 10);

export function IncomingForm({ shelves, close, onSaved }) {
  const [form, setForm] = useState({ title: "", author: "", isbn: "", category: "Umum", shelf: shelves[0]?.id || "R-01", cover: "", quantity: 1, date: today(), source: "Pembelian" });
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError("");
    try { const { data } = await api.post("/incoming", { ...form, quantity: Number(form.quantity) }); onSaved(data); close(); }
    catch (err) { setError(err.response?.data?.detail || "Gagal menyimpan buku masuk"); }
    finally { setBusy(false); }
  };
  return <Modal title="Catat buku masuk" close={close}>
    <form onSubmit={submit} className="modal-form" data-testid="incoming-form">
      <PhotoBox value={form.cover} onChange={(v) => set("cover", v)} label="Sampul buku" testId="incoming-cover-box"/>
      <label>Judul buku<input data-testid="incoming-title-input" required value={form.title} onChange={(e) => set("title", e.target.value)}/></label>
      <label>Penulis<input data-testid="incoming-author-input" required value={form.author} onChange={(e) => set("author", e.target.value)}/></label>
      <div className="form-grid">
        <label>Jumlah eksemplar<input data-testid="incoming-quantity-input" type="number" min={1} max={200} required value={form.quantity} onChange={(e) => set("quantity", e.target.value)}/></label>
        <label>Tanggal masuk<input data-testid="incoming-date-input" type="date" required value={form.date} onChange={(e) => set("date", e.target.value)}/></label>
      </div>
      <div className="form-grid">
        <label>Kategori<select data-testid="incoming-category-input" value={form.category} onChange={(e) => set("category", e.target.value)}><option>Umum</option><option>Sastra</option><option>Sains</option><option>Pelajaran</option></select></label>
        <label>Rak<select data-testid="incoming-shelf-input" value={form.shelf} onChange={(e) => set("shelf", e.target.value)}>{shelves.map((s) => <option key={s.id}>{s.id}</option>)}</select></label>
      </div>
      <div className="form-grid">
        <label>Sumber<select data-testid="incoming-source-input" value={form.source} onChange={(e) => set("source", e.target.value)}><option>Pembelian</option><option>Dana BOS</option><option>Hibah</option><option>Sumbangan Siswa</option><option>Lainnya</option></select></label>
        <label>ISBN (opsional)<input data-testid="incoming-isbn-input" value={form.isbn} onChange={(e) => set("isbn", e.target.value)}/></label>
      </div>
      {error && <div className="error" data-testid="incoming-error">{error}</div>}
      <button className="primary full" data-testid="save-incoming-button" disabled={busy}><PackagePlus size={16}/> {busy ? "Menyimpan..." : `Tambah ${form.quantity || 1} eksemplar ke stok`}</button>
    </form>
  </Modal>;
}
