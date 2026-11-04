import { Minus, Plus, RotateCcw } from "lucide-react";

// Satu baris pengaturan: teks (opsional) + ukuran teks (persen dari ukuran bawaan)
function TextRow({ id, label, hint, value, onText, maxLength = 120, size, onSize, onFocus, upper, inputTestId }) {
  const pct = size || 100;
  const step = (d) => onSize(Math.max(50, Math.min(200, pct + d)));
  return <div className="ct-row" data-testid={`ct-row-${id}`}>
    <div className="ct-head"><b>{label}</b>{hint && <small className="muted">{hint}</small>}</div>
    {onText && <input data-testid={inputTestId || `ct-text-${id}`} maxLength={maxLength} value={value} onFocus={onFocus} onChange={(e) => onText(upper ? e.target.value.toUpperCase() : e.target.value)}/>}
    <div className="ct-size">
      <span className="ct-size-label">Ukuran</span>
      <button type="button" className="ct-step" aria-label={`Perkecil ${label}`} data-testid={`ct-minus-${id}`} onClick={() => { onFocus && onFocus(); step(-5); }}><Minus size={14}/></button>
      <input type="range" className="range-input" min={50} max={200} step={5} value={pct} data-testid={`ct-size-${id}`} onFocus={onFocus} onChange={(e) => onSize(Number(e.target.value))} aria-label={`Ukuran ${label}`}/>
      <button type="button" className="ct-step" aria-label={`Perbesar ${label}`} data-testid={`ct-plus-${id}`} onClick={() => { onFocus && onFocus(); step(5); }}><Plus size={14}/></button>
      <span className={pct === 100 ? "ct-val" : "ct-val changed"} data-testid={`ct-val-${id}`}>{pct}%</span>
    </div>
  </div>;
}

export function CardTextControls({ draft, set, side, setSide }) {
  const sizes = draft.card_text_sizes || {};
  const setSize = (key) => (v) => { const next = { ...sizes }; if (v === 100) delete next[key]; else next[key] = v; set({ card_text_sizes: next }); };
  const front = () => side !== "depan" && setSide("depan");
  const back = () => side !== "belakang" && setSide("belakang");
  const changed = Object.keys(sizes).length > 0;
  const row = (id, label, extra) => <TextRow key={id} id={id} label={label} size={sizes[id]} onSize={setSize(id)} {...extra}/>;
  return <div className="control-group ct-group" data-testid="card-text-controls">
    <div className="ct-title"><span className="control-label">Teks &amp; ukuran teks di kartu</span>
      <button type="button" className="ct-reset" data-testid="ct-reset-sizes" disabled={!changed} onClick={() => set({ card_text_sizes: {} })}><RotateCcw size={13}/> Ukuran bawaan</button></div>
    <small className="muted">Ubah tulisan dan ukurannya; 100% = ukuran bawaan. Pratinjau langsung berubah, tekan Simpan desain untuk menyimpan.</small>
    <p className="ct-side">Depan kartu</p>
    {row("school", "Nama sekolah", { inputTestId: "card-school-name-input", value: draft.card_school_name, onText: (v) => set({ card_school_name: v }), onFocus: front })}
    {row("title", "Judul kartu", { inputTestId: "card-title-input", value: draft.card_title, onText: (v) => set({ card_title: v }), onFocus: front, upper: true })}
    {row("owner", "Label di atas nama", { hint: "kosongkan untuk menyembunyikan", value: draft.card_owner_label, maxLength: 40, onText: (v) => set({ card_owner_label: v }), onFocus: front })}
    {row("name", "Nama anggota", { hint: "diambil dari data anggota", onFocus: front })}
    <div className="ct-row" data-testid="ct-row-labels">
      <div className="ct-head"><b>Label Kelas &amp; NIS</b><small className="muted">Kelas tidak ikut tercetak</small></div>
      <div className="ct-pair">
        <input data-testid="ct-text-class-label" maxLength={20} value={draft.card_class_label} onFocus={front} onChange={(e) => set({ card_class_label: e.target.value })} placeholder="Kelas"/>
        <input data-testid="ct-text-nis-label" maxLength={20} value={draft.card_nis_label} onFocus={front} onChange={(e) => set({ card_nis_label: e.target.value })} placeholder="NIS"/>
      </div>
    </div>
    {row("fields", "Baris Kelas & NIS", { hint: "ukuran label dan isinya", onFocus: front })}
    {row("address", "Alamat sekolah", { hint: draft.card_show_address ? "" : "sedang disembunyikan", value: draft.card_address, onText: (v) => set({ card_address: v }), onFocus: front })}
    {row("code", "Kode anggota", { hint: "diambil dari data anggota", onFocus: front })}
    <p className="ct-side">Belakang kartu</p>
    {row("back_title", "Judul peraturan", { onFocus: back })}
    {row("back_rules", "Isi peraturan", { onFocus: back })}
    {row("back_web", "Teks web", { onFocus: back })}
  </div>;
}
