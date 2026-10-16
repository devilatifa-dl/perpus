import { useRef, useState } from "react";
import { UploadCloud, Download, FileSpreadsheet } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

export function MemberImport({ close, onDone, notify }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tplBusy, setTplBusy] = useState(false);
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  const downloadTemplate = async () => {
 fitur/laporan-kartu-belakang-cetak-duplex
    const { data } = await api.get("/members/import-template.xlsx", { responseType: "blob" });
    const url = URL.createObjectURL(data);
    const a = document.createElement("a"); a.href = url; a.download = "template-anggota.xlsx";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);

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
 main
  };

  const upload = async () => {
    if (!file) return notify("Pilih berkas Excel (.xlsx) dulu");
 fitur/laporan-kartu-belakang-cetak-duplex
    if (!file.name.toLowerCase().endsWith(".xlsx")) return notify("Hanya berkas Excel (.xlsx) yang bisa diimpor");

 main
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
      <p className="account-hint">Unggah berkas <b>Excel (.xlsx)</b> dengan kolom: <b>nama</b>, <b>nis</b>, <b>kelas</b>. Satu baris = satu anggota, dan boleh memuat banyak kelas sekaligus.</p>
<label className="import-drop" data-testid="import-file-label">
          <input ref={inputRef} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={pick} hidden />
          <FileSpreadsheet size={26} />
          <span>{file ? file.name : "Klik untuk memilih berkas Excel (.xlsx)"}</span>
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
