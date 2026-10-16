import { useState } from "react";
import { Camera } from "lucide-react";
import { api } from "../lib";

export function PhotoUploadChip({ settings, setSettings, notify }) {
  const on = settings?.member_photo_upload !== false;
  const [busy, setBusy] = useState(false);
  const toggle = async () => {
    setBusy(true);
    try {
      const { data } = await api.put("/settings/photo-upload", { enabled: !on });
      setSettings((s) => ({ ...s, ...data }));
      notify(data.member_photo_upload ? "Upload foto siswa diaktifkan" : "Upload foto siswa dinonaktifkan");
    } catch (e) { notify(e.response?.data?.detail || "Gagal mengubah pengaturan"); }
    finally { setBusy(false); }
  };
  return <button type="button" className={`photo-chip ${on ? "on" : "off"}`} disabled={busy} onClick={toggle} role="switch" aria-checked={on}
    title={on ? "Klik untuk menonaktifkan upload foto oleh siswa" : "Klik untuk mengaktifkan upload foto oleh siswa"} data-testid="photo-upload-chip" data-state={on ? "aktif" : "nonaktif"}>
    <i className="chip-dot"/><Camera size={14}/><span>Foto siswa:</span><b data-testid="photo-upload-chip-status">{on ? "Aktif" : "Nonaktif"}</b>
  </button>;
}
