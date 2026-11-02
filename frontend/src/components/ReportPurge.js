import { useState } from "react";
import { Trash2, FileSpreadsheet, ShieldAlert } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

export const PURGE_TABS = ["transaksi", "kunjungan", "masuk", "hilang"];
const LABEL = { transaksi: "Transaksi peminjaman", kunjungan: "Pengunjung", masuk: "Buku masuk", hilang: "Buku hilang" };

// Baris yang tidak boleh dihapus: buku masih dipinjam / pengunjung masih di dalam.
export const purgeLocked = (tab, r) => (tab === "transaksi" && r.status === "Dipinjam") || (tab === "kunjungan" && !r.check_out);

const saveBlob = (data, name) => {
  const url = URL.createObjectURL(data);
  const a = document.createElement("a"); a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
};

export function ReportPurge({ tab, selectedIds = [], close, onDone, notify }) {
  const thisYear = new Date().getFullYear();
  const years = Array.from({ length: 12 }, (_, i) => thisYear - i);
  const [mode, setMode] = useState(selectedIds.length ? "pilih" : "tahun");
  const [year, setYear] = useState(thisYear - 1);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  const body = () => ({ type: tab, mode, year: mode === "tahun" ? Number(year) : null, start: mode === "rentang" ? start : null, end: mode === "rentang" ? end : null, ids: mode === "pilih" ? selectedIds : [] });
  const reset = (fn) => (v) => { fn(v); setPreview(null); setErr(""); };
  const fail = async (e, msg) => {
    let m = e.response?.data?.detail;
    if (e.response?.data instanceof Blob) { try { m = JSON.parse(await e.response.data.text()).detail; } catch { m = null; } }
    setErr(typeof m === "string" ? m : msg);
  };

  const check = async () => {
    setBusy("cek"); setErr("");
    try { const { data } = await api.post("/reports/purge/preview", body()); setPreview(data); }
    catch (e) { await fail(e, "Data belum dapat diperiksa"); } finally { setBusy(""); }
  };

  const download = async () => {
    setBusy("unduh"); setErr("");
    try {
      const res = await api.post("/reports/purge/backup.xlsx", body(), { responseType: "blob" });
      saveBlob(res.data, `laporan-${tab}-${preview.label.replace(/[^0-9a-zA-Z-]+/g, "_")}.xlsx`);
      notify?.("Excel berhasil diunduh");
    } catch (e) { await fail(e, "Excel belum dapat diunduh"); } finally { setBusy(""); }
  };

  const remove = async () => {
    if (!window.confirm(`Hapus ${preview.count} data ${LABEL[tab].toLowerCase()} (${preview.label})? Data yang dihapus tidak bisa dikembalikan.`)) return;
    setBusy("hapus"); setErr("");
    try {
      const { data } = await api.post("/reports/purge", body());
      notify?.(`${data.deleted} data ${data.type_label.toLowerCase()} (${data.label}) dihapus`);
      onDone?.(); close();
    } catch (e) { await fail(e, "Gagal menghapus laporan"); } finally { setBusy(""); }
  };

  return <Modal title={`Hapus laporan ${LABEL[tab].toLowerCase()}`} close={close}>
    <div className="purge-box" data-testid="report-purge">
      <p className="account-hint">Pilih data lama yang tidak diperlukan lagi, lalu hapus atau unduh sebagai Excel.</p>
      <div className="purge-modes" role="radiogroup">
        {selectedIds.length > 0 && <button type="button" className={mode === "pilih" ? "active" : ""} data-testid="purge-mode-pilih" onClick={() => reset(setMode)("pilih")}>Terpilih ({selectedIds.length})</button>}
        <button type="button" className={mode === "tahun" ? "active" : ""} data-testid="purge-mode-tahun" onClick={() => reset(setMode)("tahun")}>Per tahun</button>
        <button type="button" className={mode === "rentang" ? "active" : ""} data-testid="purge-mode-rentang" onClick={() => reset(setMode)("rentang")}>Rentang tanggal</button>
      </div>
      {mode === "tahun" && <label>Tahun<select data-testid="purge-year-select" value={year} onChange={(e) => reset(setYear)(e.target.value)}>{years.map((y) => <option key={y} value={y}>{y}</option>)}</select></label>}
      {mode === "rentang" && <div className="purge-range">
        <label>Dari tanggal<input type="date" data-testid="purge-start-input" value={start} onChange={(e) => reset(setStart)(e.target.value)}/></label>
        <label>Sampai tanggal<input type="date" data-testid="purge-end-input" value={end} onChange={(e) => reset(setEnd)(e.target.value)}/></label>
      </div>}
      {!preview && <button className="secondary full" data-testid="purge-check-button" disabled={!!busy || (mode === "rentang" && (!start || !end))} onClick={check}>{busy === "cek" ? "Memeriksa..." : "Periksa jumlah data"}</button>}
      {preview && <div className={`purge-preview ${preview.count ? "" : "empty"}`} data-testid="purge-preview">
        <ShieldAlert size={20}/>
        <div><b data-testid="purge-preview-count">{preview.count} data ditemukan</b>
          <small>{preview.type_label} · {preview.label}</small>
          {preview.protected > 0 && <small className="purge-protected" data-testid="purge-protected">{preview.protected} data tidak ikut dihapus ({tab === "transaksi" ? "buku masih dipinjam" : "pengunjung masih di dalam"})</small>}
        </div>
      </div>}
      {preview && preview.count > 0 && <div className="purge-actions">
        <button className="danger" data-testid="purge-delete-button" disabled={!!busy} onClick={remove}><Trash2 size={16}/> {busy === "hapus" ? "Menghapus..." : `Hapus ${preview.count} data`}</button>
        <button className="secondary" data-testid="purge-download-button" disabled={!!busy} onClick={download}><FileSpreadsheet size={16}/> {busy === "unduh" ? "Menyiapkan..." : "Unduh Excel"}</button>
      </div>}
      {err && <div className="error" data-testid="purge-error">{err}</div>}
    </div>
  </Modal>;
}
