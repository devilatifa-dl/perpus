import { useState } from "react";
import { Save } from "lucide-react";
import { CARD_LAYOUTS, CARD_FONTS, CARD_FONT_SIZES, CARD_POS, CARD_PRESETS, DEFAULT_SETTINGS } from "../lib";
import { Modal, PhotoBox } from "./Shared";
import { MemberCard } from "./MemberCard";
import { MemberCardBack } from "./MemberCardBack";

export function CardDesigner({ settings, member, onSave, close }) {
  const [draft, setDraft] = useState({ ...DEFAULT_SETTINGS, ...(settings || {}) });
  const [saving, setSaving] = useState(false); const [side, setSide] = useState("depan");
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));
  const save = async () => { setSaving(true); try { await onSave(draft); close(); } finally { setSaving(false); } };
  const preview = member || { id: "MB-CONTOH01", name: "Nama Anggota", class_name: "XI IPA 1", student_id: "24000", photo: "" };
  return <Modal title="Desain kartu anggota" close={close} wide>
    <div className="designer" data-testid="card-designer">
      <div className="designer-preview"><p className="eyebrow">PRATINJAU LANGSUNG</p>
        <div className="mode-switch side-switch" data-testid="designer-side-switch">{[["depan", "Depan"], ["belakang", "Belakang"]].map(([id, l]) => <button key={id} type="button" data-testid={`designer-side-${id}`} className={side === id ? "selected" : ""} onClick={() => setSide(id)}>{l}</button>)}</div>
        {side === "depan" ? <MemberCard member={preview} settings={draft}/> : <MemberCardBack settings={draft} testId="designer-card-back"/>}</div>
      <div className="designer-controls">
        <div className="control-group back-controls" data-testid="card-back-controls"><span className="control-label">Bagian belakang kartu</span>
          <label>Judul peraturan<input data-testid="card-back-title-input" maxLength={120} value={draft.card_back_title} onFocus={() => setSide("belakang")} onChange={(e) => set({ card_back_title: e.target.value.toUpperCase() })}/></label>
          <label>Peraturan, syarat &amp; ketentuan <small className="muted">(satu baris = satu poin)</small><textarea data-testid="card-back-rules-input" rows={6} maxLength={2000} value={draft.card_back_rules} onFocus={() => setSide("belakang")} onChange={(e) => set({ card_back_rules: e.target.value })}/></label>
          <label>Teks web<input data-testid="card-back-web-input" maxLength={150} placeholder="mis. perpustakaan.sekolah.sch.id" value={draft.card_back_web} onFocus={() => setSide("belakang")} onChange={(e) => set({ card_back_web: e.target.value })}/></label>
          <small className="muted">Kosongkan teks web jika tidak ingin ditampilkan.</small>
        </div>
        <div className="control-group"><span className="control-label">Template siap pakai</span>
          <div className="pill-options">{CARD_PRESETS.map(([id, label, preset]) => <button key={id} type="button" data-testid={`preset-${id}-button`} className="pill-option preset-pill" onClick={() => set(preset)}>{label}</button>)}</div>
          <small className="muted">Pilih template untuk mengatur tema, font, dan posisi sekaligus, lalu sesuaikan bila perlu dan tekan Simpan.</small>
        </div>
        <div className="control-group"><span className="control-label">Susunan</span>
          <div className="layout-options">{CARD_LAYOUTS.map(([id, label, desc]) => <button key={id} type="button" data-testid={`layout-${id}-button`} className={draft.card_layout === id ? "layout-option active" : "layout-option"} onClick={() => set({ card_layout: id })}><b>{label}</b><small>{desc}</small></button>)}</div>
        </div>
        <div className="control-group"><span className="control-label">Jenis font</span>
          <div className="pill-options">{CARD_FONTS.map(([id, label]) => <button key={id} type="button" data-testid={`font-${id}-button`} className={draft.card_font === id ? `pill-option font-prev-${id} active` : `pill-option font-prev-${id}`} onClick={() => set({ card_font: id })}>{label}</button>)}</div>
        </div>
        <div className="control-group"><span className="control-label">Ukuran font</span>
          <div className="pill-options">{CARD_FONT_SIZES.map(([id, label]) => <button key={id} type="button" data-testid={`fontsize-${id}-button`} className={draft.card_font_size === id ? "pill-option active" : "pill-option"} onClick={() => set({ card_font_size: id })}>{label}</button>)}</div>
        </div>
        <div className="control-group"><span className="control-label">Posisi logo sekolah</span>
          <div className="pill-options">{CARD_POS.logo.map(([id, label]) => <button key={id} type="button" data-testid={`schoollogopos-${id}-button`} className={draft.card_school_logo_pos === id ? "pill-option active" : "pill-option"} onClick={() => set({ card_school_logo_pos: id })}>{label}</button>)}</div>
        </div>
        <div className="control-group"><span className="control-label">Posisi logo perpustakaan</span>
          <div className="pill-options">{CARD_POS.logo.map(([id, label]) => <button key={id} type="button" data-testid={`liblogopos-${id}-button`} className={draft.card_library_logo_pos === id ? "pill-option active" : "pill-option"} onClick={() => set({ card_library_logo_pos: id })}>{label}</button>)}</div>
        </div>
        <div className="control-group"><span className="control-label">Posisi foto</span>
          <div className="pill-options">{CARD_POS.photo.map(([id, label]) => <button key={id} type="button" data-testid={`photopos-${id}-button`} className={draft.card_photo_pos === id ? "pill-option active" : "pill-option"} onClick={() => set({ card_photo_pos: id })}>{label}</button>)}</div>
        </div>
        <div className="control-group"><span className="control-label">Posisi QR Code</span>
          <div className="pill-options">{CARD_POS.qr.map(([id, label]) => <button key={id} type="button" data-testid={`qrpos-${id}-button`} className={draft.card_qr_pos === id ? "pill-option active" : "pill-option"} onClick={() => set({ card_qr_pos: id })}>{label}</button>)}</div>
        </div>
        <label>Nama sekolah<input data-testid="card-school-name-input" value={draft.card_school_name} onChange={(e) => set({ card_school_name: e.target.value })}/></label>
        <label>Judul kartu<input data-testid="card-title-input" value={draft.card_title} onChange={(e) => set({ card_title: e.target.value.toUpperCase() })}/></label>
        <div className="toggles">
          <label className="toggle"><input type="checkbox" data-testid="card-show-qr-toggle" checked={draft.card_show_qr} onChange={(e) => set({ card_show_qr: e.target.checked })}/> Tampilkan QR Code</label>
          <label className="toggle"><input type="checkbox" data-testid="card-show-address-toggle" checked={draft.card_show_address} onChange={(e) => set({ card_show_address: e.target.checked })}/> Tampilkan alamat sekolah</label>
        </div>
        <div className="control-group"><span className="control-label">Logo</span>
          <PhotoBox compact value={draft.school_logo} onChange={(v) => set({ school_logo: v })} label="Logo sekolah" testId="school-logo-box"/>
          <PhotoBox compact value={draft.library_logo} onChange={(v) => set({ library_logo: v })} label="Logo perpustakaan" testId="library-logo-box"/>
          <small className="muted">Kosongkan untuk memakai logo bawaan.</small>
        </div>
        <button className="primary full" data-testid="save-card-design-button" disabled={saving} onClick={save}><Save size={16}/> {saving ? "Menyimpan..." : "Simpan desain"}</button>
      </div>
    </div>
  </Modal>;
}
