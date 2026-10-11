import { useState } from "react";
import { Check, Save } from "lucide-react";
import { CARD_LAYOUTS, CARD_THEMES, DEFAULT_SETTINGS } from "../lib";
import { Modal, PhotoBox } from "./Shared";
import { MemberCard } from "./MemberCard";

export function CardDesigner({ settings, member, onSave, close }) {
  const [draft, setDraft] = useState({ ...DEFAULT_SETTINGS, ...(settings || {}) });
  const [saving, setSaving] = useState(false);
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));
  const save = async () => { setSaving(true); try { await onSave(draft); close(); } finally { setSaving(false); } };
  const preview = member || { id: "MB-CONTOH01", name: "Nama Anggota", class_name: "XI IPA 1", student_id: "24000", photo: "" };
  return <Modal title="Desain kartu anggota" close={close} wide>
    <div className="designer" data-testid="card-designer">
      <div className="designer-preview"><p className="eyebrow">PRATINJAU LANGSUNG</p><MemberCard member={preview} settings={draft}/></div>
      <div className="designer-controls">
        <div className="control-group"><span className="control-label">Tema warna</span>
          <div className="swatches">{CARD_THEMES.map(([id, label]) => <button key={id} type="button" title={label} data-testid={`theme-${id}-button`} className={`swatch theme-${id} ${draft.card_theme === id ? "active" : ""}`} onClick={() => set({ card_theme: id })}>{draft.card_theme === id && <Check size={14}/>}</button>)}</div>
          <small className="muted">{CARD_THEMES.find(([id]) => id === draft.card_theme)?.[1]}</small>
        </div>
        <div className="control-group"><span className="control-label">Susunan</span>
          <div className="layout-options">{CARD_LAYOUTS.map(([id, label, desc]) => <button key={id} type="button" data-testid={`layout-${id}-button`} className={draft.card_layout === id ? "layout-option active" : "layout-option"} onClick={() => set({ card_layout: id })}><b>{label}</b><small>{desc}</small></button>)}</div>
        </div>
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
