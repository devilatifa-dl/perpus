import { useRef, useState } from "react";
import { UploadCloud, Download, FileSpreadsheet } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

function FailedRows({ rows, notify }) {
  const [busy, setBusy] = useState(false);
  const download = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/members/import-failed.xlsx", rows, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a"); a.href = url; a.download = "anggota-gagal-impor.xlsx";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1500);
    } catch (e) { notify("Daftar baris gagal belum dapat diunduh"); } finally { setBusy(false); }
  };
  return <div className="failed-rows" data-testid="import-failed-rows">
    <div className="failed-head"><span data-testid="import-failed-count">{rows.length} baris gagal diimpor</span>
      <button type="button" className="secondary" data-testid="download-failed-rows-button" onClick={download} disabled={busy}><Download size={14}/> {busy ? "Menyiapkan..." : "Unduh Excel untuk diperbaiki"}</button></div>
    <div className="failed-table-wrap"><table className="failed-table"><thead><tr><th>Baris</th><th>Nama</th><th>NIS</th><th>Kelas</th><th>Alasan</th></tr></thead>
      <tbody>{rows.map((r) => <tr key={r.row} data-testid={`import-failed-row-${r.row}`}><td>{r.row}</td><td>{r.nama || "-"}</td><td>{r.nis || "-"}</td><td>{r.kelas || "-"}</td><td className="reason">{r.alasan}</td></tr>)}</tbody></table></div>
    <small className="failed-hint">Perbaiki baris di berkas unduhan, lalu impor ulang berkas tersebut.</small>
  </div>;
}

function ListTable({ testid, title, rows, cols, hint }) {
  const [open, setOpen] = useState(rows.length <= 10);
  return <div className="failed-rows" data-testid={testid}>
    <div className="failed-head"><span data-testid={`${testid}-count`}>{title}</span>
      <button type="button" className="secondary" data-testid={`${testid}-toggle`} onClick={() => setOpen(!open)}>{open ? "Sembunyikan" : "Lihat daftar"}</button></div>
    {open && <div className="failed-table-wrap"><table className="failed-table"><thead><tr>{cols.map((c) => <th key={c[0]}>{c[0]}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={r.id || i} data-testid={`${testid}-row-${i}`}>{cols.map((c) => <td key={c[0]}>{c[1](r) || "-"}</td>)}</tr>)}</tbody></table></div>}
    {hint && <small className="failed-hint">{hint}</small>}
  </div>;
}

export function MemberImport({ close, onDone, notify }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tplBusy, setTplBusy] = useState(false);
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  const downloadTemplate = async () => {
    setTplBusy(true);
    try {
      const { data } = await api.get("/members/import-template.xlsx", { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a"); a.href = url; a.download = "template-anggota.xlsx";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1500);
    } catch (e) {
      notify("Template Excel belum dapat diunduh");
    } finally { setTplBusy(false); }
  };

  const pick = (f) => {
    setResult(null);
    if (f && !/\.xlsx$/i.test(f.name)) { setFile(null); notify("Pilih berkas Excel (.xlsx)"); return; }
    setFile(f || null);
  };

  const upload = async () => {
    if (!file) return notify("Pilih berkas Excel (.xlsx) dulu");
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/members/import", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(data);
      notify(`${data.imported} anggota baru, ${data.updated || 0} kelas diperbarui, ${data.skipped} dilewati`);
      onDone();
    } catch (e) {
      notify(e.response?.data?.detail || "Gagal mengimpor berkas");
    } finally { setBusy(false); }
  };

  return <Modal title="Impor anggota massal" close={close}>
    <div className="import-box" data-testid="member-import">
      <p className="account-hint">Unggah berkas <b>Excel (.xlsx)</b> dengan kolom: <b>nama</b>, <b>nis</b>, <b>kelas</b>. Satu baris = satu anggota, dan boleh memuat banyak kelas sekaligus. <b>Kenaikan kelas:</b> NIS yang sudah terdaftar hanya diperbarui kelasnya.</p>
      <button type="button" className="secondary" data-testid="download-template-button" onClick={downloadTemplate} disabled={tplBusy}><Download size={15}/> {tplBusy ? "Menyiapkan..." : "Unduh template Excel"}</button>
      <label className="import-drop" data-testid="import-file-label" onClick={() => inputRef.current?.click()}>
        <input ref={inputRef} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" data-testid="import-file-input" onChange={(e) => pick(e.target.files[0])} style={{ display: "none" }}/>
        <FileSpreadsheet size={26}/>
        <span>{file ? file.name : "Klik untuk memilih berkas Excel"}</span>
      </label>
      {result && <div className="import-result" data-testid="import-result">
        <b>Hasil impor</b>
        <span data-testid="import-summary">Anggota baru: {result.imported} · Kelas diperbarui: {result.updated || 0} · Tetap: {result.unchanged || 0} · Dilewati: {result.skipped} · Total baris: {result.total}</span>
        {result.class_changes?.length > 0 && <ListTable testid="import-class-changes" title={`${result.class_changes.length} siswa pindah kelas`} rows={result.class_changes}
          cols={[["Nama", (r) => r.name], ["NIS", (r) => r.nis], ["Kelas lama", (r) => r.from], ["Kelas baru", (r) => r.to]]}
          hint="Riwayat pinjam & kunjungan tetap tersambung. Laporan lama tetap memakai kelas saat transaksi terjadi."/>}
        {result.errors?.length > 0 && <FailedRows rows={result.errors} notify={notify}/>}
        {result.not_in_file?.length > 0 && <ListTable testid="import-not-in-file" title={`${result.not_in_file.length} anggota terdaftar tidak ada di berkas`} rows={result.not_in_file}
          cols={[["Nama", (r) => r.name], ["NIS", (r) => r.nis], ["Kelas", (r) => r.kelas]]}
          hint="Data mereka tidak diubah. Jika sudah lulus/pindah, hapus manual dari menu Anggota."/>}
      </div>}
      <button className="primary full" data-testid="do-import-button" disabled={busy || !file} onClick={upload}><UploadCloud size={16}/> {busy ? "Mengimpor..." : "Impor sekarang"}</button>
    </div>
  </Modal>;
}
