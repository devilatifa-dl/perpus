import { useEffect, useState } from "react";
import { BookOpen, Lock } from "lucide-react";
import { api, fmtDate, uploadPhoto } from "../lib";
import { PhotoBox } from "./Shared";
import { MemberCard } from "./MemberCard";

export function StudentProfile({ settings, notify }) {
  const [member, setMember] = useState(null); const [hist, setHist] = useState(null); const [draft, setDraft] = useState(""); const [saving, setSaving] = useState(false);
  const allowed = settings?.member_photo_upload !== false;
  useEffect(() => {
    api.get("/account/member").then((r) => { setMember(r.data); setDraft(r.data?.photo || ""); }).catch(() => {});
    api.get("/account/history").then((r) => setHist(r.data)).catch(() => setHist({ history: [], total: 0, active: 0 }));
  }, []);
  const save = async () => {
    setSaving(true);
    try { const { data } = await api.post(`/members/${member.id}/photo`, { photo: draft }); setMember(data); notify("Foto berhasil diunggah — kartu anggota diperbarui"); }
    catch (e) { notify(e.response?.data?.detail || "Gagal menyimpan foto"); }
    finally { setSaving(false); }
  };
  if (!member) return <div className="panel muted" data-testid="student-profile-loading">Memuat profil...</div>;
  return <div className="profile-grid" data-testid="student-profile-tab">
    <div className="panel">
      <p className="eyebrow">KARTU ANGGOTA SAYA</p>
      <MemberCard member={{ ...member, photo: draft }} settings={settings}/>
      <div className="profile-actions">
        {allowed ? <>
          <PhotoBox value={draft} onChange={setDraft} label="Foto profil" testId="profile-photo-box" upload={uploadPhoto} onError={notify}/>
          <button className="primary full" data-testid="save-profile-photo-button" disabled={saving || draft === (member.photo || "")} onClick={save}>{saving ? "Menyimpan..." : "Simpan foto"}</button>
        </> : <div className="photo-locked" data-testid="photo-upload-locked"><Lock size={16}/> Upload foto sedang ditutup admin</div>}
      </div>
    </div>
    <div className="panel" data-testid="student-history">
      <div className="panel-title"><div><p className="eyebrow">RIWAYAT PINJAM</p><h3>{hist ? `${hist.total} peminjaman · ${hist.active} masih dipinjam` : "Memuat..."}</h3></div></div>
      {hist && hist.history.length === 0 && <p className="muted" data-testid="student-history-empty">Belum pernah meminjam buku.</p>}
      {hist?.history.map((h) => <div className="mini-transaction" key={h.id} data-testid={`student-history-${h.id}`}>
        <div className={`activity-icon ${h.returned ? "return" : "borrow"}`}><BookOpen size={15}/></div>
        <div><b>{h.book_title}</b><span>Dipinjam {fmtDate(h.date)}{h.returned ? ` · kembali ${fmtDate(h.returned_at)}` : ""}</span></div>
        <span className={`status ${h.returned ? "tersedia" : "dipinjam"}`}>{h.returned ? "Dikembalikan" : "Dipinjam"}</span>
      </div>)}
    </div>
  </div>;
}
