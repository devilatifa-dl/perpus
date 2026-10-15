import { useEffect, useState } from "react";
import { Camera, CameraOff, Clock, Save } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";

export const fmtUntil = (iso) => iso ? new Date(iso).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }) + " WIB" : "";
const toLocalInput = (iso) => { if (!iso) return ""; const d = new Date(iso); const p = (n) => String(n).padStart(2, "0"); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`; };
const inHours = (h) => toLocalInput(new Date(Date.now() + h * 3600 * 1000).toISOString());
const todayAt = (hh) => { const d = new Date(); d.setHours(hh, 0, 0, 0); if (d < new Date()) d.setDate(d.getDate() + 1); return toLocalInput(d.toISOString()); };

/** Tombol status + pengaturan izin unggah foto oleh siswa (khusus admin/petugas). */
export function StudentPhotoSwitch({ notify }) {
  const [cfg, setCfg] = useState(null); const [open, setOpen] = useState(false);
  const [until, setUntil] = useState(""); const [replace, setReplace] = useState(true); const [saving, setSaving] = useState(false);
  const load = () => api.get("/settings/student-photo").then((r) => setCfg(r.data)).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t); }, []);
  const openModal = () => { setUntil(toLocalInput(cfg?.until)); setReplace(cfg?.allow_replace ?? true); setOpen(true); };
  const save = async (patch, msg) => {
    setSaving(true);
    try {
      const body = { enabled: cfg?.enabled ?? true, until: cfg?.until || "", allow_replace: cfg?.allow_replace ?? true, ...patch };
      const { data } = await api.put("/settings/student-photo", body);
      setCfg(data); if (msg) notify(msg(data));
      return data;
    } catch (e) { notify(e.response?.data?.detail || "Pengaturan gagal disimpan"); return null; }
    finally { setSaving(false); }
  };
  const toggle = () => save({ enabled: !(cfg?.open), until: cfg?.open ? cfg.until : (cfg?.until && new Date(cfg.until) > new Date() ? cfg.until : "") },
    (d) => d.open ? "Unggah foto siswa DIAKTIFKAN" : "Unggah foto siswa DINONAKTIFKAN");
  const saveDetail = async (e) => {
    e.preventDefault();
    if (until && new Date(until) <= new Date()) { notify("Batas waktu harus setelah sekarang"); return; }
    const d = await save({ until: until ? new Date(until).toISOString() : "", allow_replace: replace }, () => "Pengaturan unggah foto disimpan");
    if (d) setOpen(false);
  };
  const on = !!cfg?.open;
  const expired = cfg && cfg.enabled && !cfg.open;
  return <>
    <button className={`secondary photo-switch-btn ${on ? "on" : "off"}`} data-testid="student-photo-switch-button" onClick={openModal} disabled={!cfg} title="Atur izin unggah foto oleh siswa">
      <span className="dot"/>{on ? <Camera size={16}/> : <CameraOff size={16}/>} Foto siswa: <b data-testid="student-photo-switch-state">{cfg ? (on ? "Aktif" : "Nonaktif") : "..."}</b>
    </button>
    {open && cfg && <Modal title="Izin unggah foto siswa" close={() => setOpen(false)}>
      <div className="photo-switch" data-testid="student-photo-settings">
        <div className={`photo-switch-main ${on ? "on" : "off"}`}>
          <div>
            <b>{on ? "Siswa BOLEH unggah foto" : "Siswa TIDAK BISA unggah foto"}</b>
            <small data-testid="student-photo-status-text">{on ? (cfg.until ? `Tutup otomatis ${fmtUntil(cfg.until)}` : "Terbuka tanpa batas waktu") : expired ? `Ditutup otomatis sejak ${fmtUntil(cfg.until)}` : "Tombol unggah foto di portal siswa dikunci"}</small>
          </div>
          <button type="button" role="switch" aria-checked={on} className={`switch ${on ? "on" : ""}`} data-testid="student-photo-toggle" disabled={saving} onClick={toggle}><span/></button>
        </div>
        <form className="modal-form" onSubmit={saveDetail}>
          <label>Tutup otomatis pada (opsional)
            <input type="datetime-local" data-testid="student-photo-until-input" value={until} onChange={(e) => setUntil(e.target.value)}/>
          </label>
          <div className="chip-row">
            <button type="button" className="chip" data-testid="until-1h" onClick={() => setUntil(inHours(1))}><Clock size={12}/> 1 jam lagi</button>
            <button type="button" className="chip" data-testid="until-2h" onClick={() => setUntil(inHours(2))}><Clock size={12}/> 2 jam lagi</button>
            <button type="button" className="chip" data-testid="until-14" onClick={() => setUntil(todayAt(14))}><Clock size={12}/> Jam 14:00</button>
            <button type="button" className="chip" data-testid="until-none" onClick={() => setUntil("")}>Tanpa batas</button>
          </div>
          <label className="check-row"><input type="checkbox" data-testid="student-photo-replace-checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)}/><span><b>Boleh mengganti foto yang sudah ada</b><small>Jika tidak dicentang, siswa hanya bisa mengunggah untuk anggota yang belum berfoto.</small></span></label>
          <p className="account-hint" style={{ margin: 0 }}>Admin &amp; petugas tetap bisa mengubah foto kapan saja dari menu Anggota.{cfg.updated_by ? ` Terakhir diubah oleh ${cfg.updated_by}.` : ""}</p>
          <button className="primary full" data-testid="save-student-photo-settings" disabled={saving}><Save size={16}/> Simpan pengaturan</button>
        </form>
      </div>
    </Modal>}
  </>;
}
