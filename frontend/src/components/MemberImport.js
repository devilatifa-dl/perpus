import { useRef, useState } from "react";
import { UploadCloud, Download, FileSpreadsheet } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

export function MemberImport({ close, onDone, notify }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  const downloadTemplate = () => {
    const csv = "nama,nis,kelas\nBudi Santoso,24100,X IPA 1\nSiti Aminah,24101,X IPA 1\nRudi Hartono,24102,X IPS 2\n";
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "template-anggota.csv";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const upload = async () => {
    if (!file) return notify("Pilih berkas .csv atau .xlsx dulu");
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/members/import", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(data);
      notify(`${data.imported} anggota diimpor, ${data.skipped} dilewati`);
      onDone();
    } catch (e) {
      notify(e.response?.data?.detail || "Gagal mengimpor berkas");
    } finally { setBusy(false); }
  };

  return <Modal title="Impor anggota massal" close={close}>
    <div className="import-box" data-testid="member-import">
      <p className="account-hint">Unggah berkas <b>.csv</b> atau <b>.xlsx</b> dengan kolom: <b>nama</b>, <b>nis</b>, <b>kelas</b>. Satu baris = satu anggota, dan boleh memuat banyak kelas sekaligus.</p>
      <button type="button" className="secondary" data-testid="download-template-button" onClick={downloadTemplate}><Download size={15}/> Unduh template CSV</button>
      <label className="import-drop" data-testid="import-file-label" onClick={() => inputRef.current?.click()}>
        <input ref={inputRef} type="file" accept=".csv,.xlsx" data-testid="import-file-input" onChange={(e) => { setFile(e.target.files[0]); setResult(null); }} style={{ display: "none" }}/>
        <FileSpreadsheet size={26}/>
        <span>{file ? file.name : "Klik untuk memilih berkas"}</span>
      </label>
      {result && <div className="import-result" data-testid="import-result">
        <b>Hasil impor</b>
        <span>Berhasil: {result.imported} · Dilewati: {result.skipped} · Total baris: {result.total}</span>
        {result.errors?.length > 0 && <ul>{result.errors.map((er, i) => <li key={i}>{er}</li>)}</ul>}
      </div>}
      <button className="primary full" data-testid="do-import-button" disabled={busy || !file} onClick={upload}><UploadCloud size={16}/> {busy ? "Mengimpor..." : "Impor sekarang"}</button>
    </div>
  </Modal>;
}
