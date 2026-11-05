import { Minus, Plus, RotateCcw } from "lucide-react";
import { CARD_FONTS } from "../lib";

// Satu baris pengaturan elemen kartu: (tampil/sembunyi) + teks + jenis font + ukuran (persen dari bawaan)
export function TextRow({ id, label, hint, value, onText, maxLength = 120, size, onSize, font, onFont, onFocus, upper, inputTestId, shown, onShown, multiline, rows = 4, placeholder, children }) {
  const pct = size || 100;
  const step = (d) => { onFocus && onFocus(); onSize(Math.max(50, Math.min(200, pct + d))); };
  const hidden = shown === false;
  const TextTag = multiline ? "textarea" : "input";
  return <div className={`ct-row${hidden ? " is-hidden" : ""}`} data-testid={`ct-row-${id}`}>
    <div className="ct-head"><b>{label}</b>{hint && <small className="muted">{hint}</small>}
      {onShown && <label className="ct-show" title={hidden ? "Tampilkan di kartu" : "Sembunyikan dari kartu"}><input type="checkbox" data-testid={`ct-show-${id}`} checked={!hidden} onChange={(e) => { onFocus && onFocus(); onShown(e.target.checked); }}/><span>{hidden ? "Disembunyikan" : "Tampil"}</span></label>}
    </div>
    {onText && <TextTag data-testid={inputTestId || `ct-text-${id}`} maxLength={maxLength} rows={multiline ? rows : undefined} placeholder={placeholder} value={value} onFocus={onFocus} onChange={(e) => onText(upper ? e.target.value.toUpperCase() : e.target.value)} disabled={hidden}/>}
    {children}
    <div className="ct-tools">
      <select className="ct-font" aria-label={`Font ${label}`} data-testid={`ct-font-${id}`} value={font || ""} onFocus={onFocus} onChange={(e) => onFont(e.target.value)} disabled={hidden}>
        <option value="">Font: ikuti kartu</option>
        {CARD_FONTS.map(([fid, l]) => <option key={fid} value={fid}>{l}</option>)}
      </select>
      <div className="ct-stepper" role="group" aria-label={`Ukuran ${label}`}>
        <button type="button" className="ct-step" aria-label={`Perkecil ${label}`} data-testid={`ct-minus-${id}`} onClick={() => step(-5)} disabled={hidden || pct <= 50}><Minus size={13}/></button>
        <button type="button" className={pct === 100 ? "ct-val" : "ct-val changed"} title="Klik untuk kembali 100%" data-testid={`ct-val-${id}`} onClick={() => onSize(100)} disabled={hidden}>{pct}%</button>
        <button type="button" className="ct-step" aria-label={`Perbesar ${label}`} data-testid={`ct-plus-${id}`} onClick={() => step(5)} disabled={hidden || pct >= 200}><Plus size={13}/></button>
      </div>
    </div>
  </div>;
}

// Pengaturan semua teks kartu. group = "depan" | "belakang"
export function CardTextControls({ draft, set, group = "depan", setSide }) {
  const sizes = draft.card_text_sizes || {};
  const fonts = draft.card_text_fonts || {};
  const setSize = (key) => (v) => { const next = { ...sizes }; if (v === 100) delete next[key]; else next[key] = v; if (key === "class" || key === "nis") delete next.fields; set({ card_text_sizes: next }); };
  const setFont = (key) => (v) => { const next = { ...fonts }; if (!v) delete next[key]; else next[key] = v; set({ card_text_fonts: next }); };
  const focus = () => setSide && setSide(group);
  // Ukuran lama "fields" (Kelas & NIS bersama) tetap dihormati sampai diubah
  const sizeOf = (id) => sizes[id] ?? ((id === "class" || id === "nis") ? sizes.fields : undefined);
  const row = (id, label, extra = {}) => <TextRow key={id} id={id} label={label} size={sizeOf(id)} onSize={setSize(id)} font={fonts[id]} onFont={setFont(id)} onFocus={focus} {...extra}/>;
  const keys = group === "depan" ? ["school", "title", "owner", "name", "class", "nis", "fields", "address", "code"] : ["back_title", "back_rules", "back_web"];
  const changed = keys.some((k) => k in sizes || k in fonts);
  const reset = () => { const s2 = { ...sizes }; const f2 = { ...fonts }; keys.forEach((k) => { delete s2[k]; delete f2[k]; }); set({ card_text_sizes: s2, card_text_fonts: f2 }); };
  return <div className="ct-group" data-testid={group === "depan" ? "card-text-controls" : "card-back-controls"}>
    <div className="ct-title"><small className="muted">Ubah tulisan, jenis font, dan ukuran tiap bagian. 100% = ukuran bawaan.</small>
      <button type="button" className="ct-reset" data-testid={group === "depan" ? "ct-reset-sizes" : "ct-reset-back"} disabled={!changed} onClick={reset}><RotateCcw size={12}/> Atur ulang</button></div>
    {group === "depan" ? <>
      {row("school", "Nama sekolah", { inputTestId: "card-school-name-input", value: draft.card_school_name, onText: (v) => set({ card_school_name: v }) })}
      {row("title", "Judul kartu", { inputTestId: "card-title-input", value: draft.card_title, onText: (v) => set({ card_title: v }), upper: true })}
      {row("owner", "Label di atas nama", { hint: "kosongkan untuk menyembunyikan", value: draft.card_owner_label, maxLength: 40, onText: (v) => set({ card_owner_label: v }) })}
      {row("name", "Nama anggota", { hint: "dari data anggota" })}
      {row("class", "Kelas", { hint: "tidak ikut tercetak", inputTestId: "ct-text-class-label", placeholder: "Kelas", value: draft.card_class_label, maxLength: 20, onText: (v) => set({ card_class_label: v }), shown: draft.card_show_class !== false, onShown: (v) => set({ card_show_class: v }) })}
      {row("nis", "NIS", { inputTestId: "ct-text-nis-label", placeholder: "NIS", value: draft.card_nis_label, maxLength: 20, onText: (v) => set({ card_nis_label: v }), shown: draft.card_show_nis !== false, onShown: (v) => set({ card_show_nis: v }) })}
      {row("address", "Alamat sekolah", { value: draft.card_address, onText: (v) => set({ card_address: v }), shown: draft.card_show_address !== false, onShown: (v) => set({ card_show_address: v }) })}
      {row("code", "Kode anggota", { hint: "dari data anggota", shown: draft.card_show_code !== false, onShown: (v) => set({ card_show_code: v }) })}
    </> : <>
      {row("back_title", "Judul peraturan", { inputTestId: "card-back-title-input", value: draft.card_back_title, onText: (v) => set({ card_back_title: v }), upper: true })}
      {row("back_rules", "Peraturan & ketentuan", { hint: "satu baris = satu poin", inputTestId: "card-back-rules-input", value: draft.card_back_rules, maxLength: 2000, multiline: true, rows: 5, onText: (v) => set({ card_back_rules: v }) })}
      {row("back_web", "Teks web", { hint: "kosongkan bila tidak dipakai", inputTestId: "card-back-web-input", placeholder: "mis. perpustakaan.sekolah.sch.id", value: draft.card_back_web, maxLength: 150, onText: (v) => set({ card_back_web: v }) })}
    </>}
  </div>;
}
