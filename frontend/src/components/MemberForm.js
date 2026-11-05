import { GraduationCap, Lock, UserRound } from "lucide-react";
import { PhotoBox } from "./Shared";
import { uploadPhoto } from "../lib";

export const isGuru = (m) => (m?.member_type || "siswa") === "guru";
export const EMPTY_MEMBER = { name: "", student_id: "", class_name: "", subject: "", member_type: "siswa", photo: "" };
export const memberToForm = (m) => ({ name: m.name || "", student_id: m.student_id || "", class_name: isGuru(m) ? "" : (m.class_name || ""), subject: m.subject || "", member_type: isGuru(m) ? "guru" : "siswa", photo: m.photo || "" });

const TYPES = [["siswa", "Siswa", GraduationCap], ["guru", "Guru", UserRound]];

// Formulir tambah / edit anggota: pilihan tipe Siswa (NIS + Kelas) atau Guru (Mata Pelajaran)
export function MemberForm({ form, setForm, onSubmit, prefix = "member", submitLabel, submitTestId, photoTestId, photoLocked, notify }) {
  const guru = form.member_type === "guru";
  const set = (k, v) => setForm({ ...form, [k]: v });
  const fields = guru ? [["name", "Nama lengkap"], ["subject", "Mata Pelajaran"]] : [["name", "Nama lengkap"], ["student_id", "NIS"], ["class_name", "Kelas"]];
  return <form onSubmit={onSubmit} className="modal-form" data-testid={`${prefix}-form`}>
    <div className="member-type-field">
      <span>Tipe anggota</span>
      <div className="member-type-switch" role="radiogroup" aria-label="Tipe anggota" data-testid={`${prefix}-type-switch`}>
        {TYPES.map(([id, label, Icon]) => <button key={id} type="button" role="radio" aria-checked={form.member_type === id} className={form.member_type === id ? "selected" : ""} data-testid={`${prefix}-type-${id}`} onClick={() => set("member_type", id)}><Icon size={16}/> {label}</button>)}
      </div>
    </div>
    {photoLocked
      ? <div className="photo-locked-box" data-testid={`${photoTestId}-locked`}>
          <div className="avatar large">{form.photo ? <img src={form.photo} alt={form.name}/> : (form.name || "?")[0]}</div>
          <div><b><Lock size={13}/> Foto sudah diunggah</b><small>Hanya admin yang dapat mengganti foto anggota.</small></div>
        </div>
      : <PhotoBox value={form.photo} onChange={(v) => set("photo", v)} label="Foto anggota" testId={photoTestId} upload={uploadPhoto} onError={notify}/>}
    {fields.map(([key, label]) => <label key={key}>{label}<input data-testid={`${prefix}-${key}-input`} required value={form[key]} placeholder={key === "subject" ? "mis. Matematika" : undefined} onChange={(e) => set(key, e.target.value)}/></label>)}
    {guru && <p className="account-hint" style={{ margin: 0 }} data-testid={`${prefix}-guru-hint`}>Anggota guru tidak memakai NIS &amp; kelas. Di daftar anggota, cetak massal, dan laporan guru dikelompokkan sebagai "Guru".</p>}
    <button className="primary full" data-testid={submitTestId}>{submitLabel}</button>
  </form>;
}
