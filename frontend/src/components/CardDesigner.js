import { useState } from "react";
import { Image as ImageIcon, LayoutTemplate, Minus, Plus, RotateCcw, Save, Type, ScrollText } from "lucide-react";
import { CARD_LAYOUTS, CARD_FONTS, CARD_FONT_SIZES, CARD_PHOTO_SHAPES, CARD_POS, CARD_PRESETS, DEFAULT_SETTINGS } from "../lib";
import { Modal, PhotoBox } from "./Shared";
import { MemberCard } from "./MemberCard";
import { MemberCardBack } from "./MemberCardBack";
import { CardTextControls } from "./CardTextControls";

const TABS = [["tampilan", "Tampilan", LayoutTemplate], ["teks", "Teks & font", Type], ["foto", "Foto & logo", ImageIcon], ["belakang", "Belakang", ScrollText]];

// Pilihan bersebelahan (segmented). testId tetap `${prefix}-${id}-button` agar kompatibel.
function Seg({ options, value, onChange, prefix }) {
  return <div className="dz-seg" role="radiogroup">{options.map(([id, label]) => <button key={id} type="button" role="radio" aria-checked={value === id} data-testid={`${prefix}-${id}-button`} className={value === id ? "pill-option active" : "pill-option"} onClick={() => onChange(id)}>{label}</button>)}</div>;
}
const Field = ({ label, children, hint }) => <div className="dz-field"><span className="control-label">{label}{hint && <small className="muted"> {hint}</small>}</span>{children}</div>;

export function CardDesigner({ settings, member, onSave, close }) {
  const [draft, setDraft] = useState({ ...DEFAULT_SETTINGS, ...(settings || {}) });
  const [saving, setSaving] = useState(false); const [side, setSide] = useState("depan"); const [tab, setTabState] = useState("tampilan");
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));
  const setTab = (t) => { setTabState(t); setSide(t === "belakang" ? "belakang" : "depan"); };
  const save = async () => { setSaving(true); try { await onSave(draft); close(); } finally { setSaving(false); } };
  const preview = member || { id: "MB-CONTOH01", name: "Nama Anggota", class_name: "XI IPA 1", student_id: "24000", photo: "" };
  const photoPct = Number(draft.card_photo_size) || 100;
  const setPhoto = (v) => set({ card_photo_size: Math.max(60, Math.min(160, v)) });
  return <Modal title="Desain kartu anggota" close={close} wide>
    <div className="designer dz" data-testid="card-designer">
      <div className="designer-preview"><p className="eyebrow">PRATINJAU LANGSUNG</p>
        <div className="mode-switch side-switch" data-testid="designer-side-switch">{[["depan", "Depan"], ["belakang", "Belakang"]].map(([id, l]) => <button key={id} type="button" data-testid={`designer-side-${id}`} className={side === id ? "selected" : ""} onClick={() => setSide(id)}>{l}</button>)}</div>
        {side === "depan" ? <MemberCard member={preview} settings={draft}/> : <MemberCardBack settings={draft} testId="designer-card-back"/>}
        <small className="muted dz-note">Perubahan langsung terlihat di sini. Tekan <b>Simpan desain</b> untuk menyimpan.</small>
      </div>
      <div className="designer-controls">
        <div className="dz-tabs" role="tablist" data-testid="designer-tabs">{TABS.map(([id, label, Icon]) => <button key={id} type="button" role="tab" aria-selected={tab === id} data-testid={`designer-tab-${id}`} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><Icon size={14}/> {label}</button>)}</div>
        <div className="dz-pane" data-testid={`designer-pane-${tab}`}>
          {tab === "tampilan" && <>
            <Field label="Template siap pakai"><div className="pill-options dz-wrap">{CARD_PRESETS.map(([id, label, preset]) => <button key={id} type="button" data-testid={`preset-${id}-button`} className="pill-option preset-pill" onClick={() => set(preset)}>{label}</button>)}</div></Field>
            <Field label="Susunan"><div className="layout-options">{CARD_LAYOUTS.map(([id, label, desc]) => <button key={id} type="button" data-testid={`layout-${id}-button`} className={draft.card_layout === id ? "layout-option active" : "layout-option"} onClick={() => set({ card_layout: id })}><b>{label}</b><small>{desc}</small></button>)}</div></Field>
            <Field label="Font utama kartu" hint="(bisa diganti per teks di tab Teks & font)"><div className="dz-fonts">{CARD_FONTS.map(([id, label]) => <button key={id} type="button" data-testid={`font-${id}-button`} className={draft.card_font === id ? `dz-font font-prev-${id} active` : `dz-font font-prev-${id}`} onClick={() => set({ card_font: id })}><span>Aa</span><small>{label}</small></button>)}</div></Field>
            <div className="dz-grid2">
              <Field label="Ukuran font"><Seg options={CARD_FONT_SIZES} value={draft.card_font_size} onChange={(v) => set({ card_font_size: v })} prefix="fontsize"/></Field>
              <Field label="Posisi QR Code"><Seg options={CARD_POS.qr} value={draft.card_qr_pos} onChange={(v) => set({ card_qr_pos: v })} prefix="qrpos"/></Field>
            </div>
            <div className="toggles dz-toggles">
              <label className="toggle"><input type="checkbox" data-testid="card-show-qr-toggle" checked={draft.card_show_qr} onChange={(e) => set({ card_show_qr: e.target.checked })}/> Tampilkan QR Code</label>
              <label className="toggle"><input type="checkbox" data-testid="card-show-address-toggle" checked={draft.card_show_address} onChange={(e) => set({ card_show_address: e.target.checked })}/> Tampilkan alamat sekolah</label>
            </div>
          </>}
          {tab === "teks" && <CardTextControls draft={draft} set={set} group="depan" setSide={setSide}/>}
          {tab === "foto" && <>
            <div className="dz-box"><p className="dz-box-title">Foto anggota</p>
              <Field label="Posisi foto"><Seg options={CARD_POS.photo} value={draft.card_photo_pos} onChange={(v) => set({ card_photo_pos: v })} prefix="photopos"/></Field>
              <Field label="Bentuk foto"><Seg options={CARD_PHOTO_SHAPES} value={draft.card_photo_shape || "membulat"} onChange={(v) => set({ card_photo_shape: v })} prefix="photoshape"/></Field>
              <Field label="Ukuran foto"><div className="dz-range" data-testid="photo-size-control">
                <button type="button" className="ct-step" aria-label="Perkecil foto" data-testid="photo-size-minus" onClick={() => setPhoto(photoPct - 5)} disabled={photoPct <= 60}><Minus size={13}/></button>
                <input type="range" className="range-input" min={60} max={160} step={5} value={photoPct} aria-label="Ukuran foto" data-testid="photo-size-range" onChange={(e) => setPhoto(Number(e.target.value))}/>
                <button type="button" className="ct-step" aria-label="Perbesar foto" data-testid="photo-size-plus" onClick={() => setPhoto(photoPct + 5)} disabled={photoPct >= 160}><Plus size={13}/></button>
                <button type="button" className={photoPct === 100 ? "ct-val" : "ct-val changed"} title="Kembali 100%" data-testid="photo-size-value" onClick={() => setPhoto(100)}>{photoPct}%</button>
              </div></Field>
            </div>
            <div className="dz-box"><p className="dz-box-title">Logo</p>
              <div className="dz-grid2">
                <Field label="Logo sekolah"><Seg options={CARD_POS.logo} value={draft.card_school_logo_pos} onChange={(v) => set({ card_school_logo_pos: v })} prefix="schoollogopos"/></Field>
                <Field label="Logo perpustakaan"><Seg options={CARD_POS.logo} value={draft.card_library_logo_pos} onChange={(v) => set({ card_library_logo_pos: v })} prefix="liblogopos"/></Field>
              </div>
              <div className="dz-grid2 dz-logos">
                <PhotoBox compact value={draft.school_logo} onChange={(v) => set({ school_logo: v })} label="Logo sekolah" testId="school-logo-box"/>
                <PhotoBox compact value={draft.library_logo} onChange={(v) => set({ library_logo: v })} label="Logo perpustakaan" testId="library-logo-box"/>
              </div>
              <small className="muted">Kosongkan untuk memakai logo bawaan.</small>
            </div>
          </>}
          {tab === "belakang" && <CardTextControls draft={draft} set={set} group="belakang" setSide={setSide}/>}
        </div>
        <div className="dz-footer">
          <button type="button" className="secondary" data-testid="reset-card-design-button" onClick={() => { if (window.confirm("Kembalikan semua pengaturan kartu ke bawaan? (logo ikut kembali ke bawaan)")) setDraft({ ...DEFAULT_SETTINGS }); }}><RotateCcw size={15}/> Bawaan</button>
          <button className="primary" data-testid="save-card-design-button" disabled={saving} onClick={save}><Save size={16}/> {saving ? "Menyimpan..." : "Simpan desain"}</button>
        </div>
      </div>
    </div>
  </Modal>;
}
