import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, CameraOff, Clock, DoorClosed, DoorOpen, LogIn, LogOut, Maximize2, Pencil, ScanLine, Trash2, UserPlus, Users } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";
import { CameraScanner } from "./CameraScanner";

const todayStr = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);
export const fmtClock = (d) => d ? new Date(d).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }) : "-";
export const fmtDur = (m) => m == null ? "-" : m >= 60 ? `${Math.floor(m / 60)} j ${m % 60} m` : `${m} menit`;
export const OUT_LABEL = { scan: "Scan keluar", manual: "Dicatat petugas", otomatis: "Otomatis" };

function beep(ok = true) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.frequency.value = ok ? 880 : 240; o.connect(g); g.connect(ctx.destination); g.gain.value = 0.08;
    o.start(); setTimeout(() => { o.stop(); ctx.close(); }, ok ? 140 : 320);
  } catch (e) { /* audio tidak tersedia */ }
}

function LiveScanner({ onCode }) {
  return <div className="visit-cam" data-testid="visit-camera"><CameraScanner onCode={onCode} testId="visit-camera-scanner"/></div>;
}

export function Visitors({ notify }) {
  const [date, setDate] = useState(todayStr()); const [data, setData] = useState({ items: [], summary: { total: 0, inside: 0, anggota: 0, tamu: 0 }, checkout_time: "14:00" });
  const [code, setCode] = useState(""); const [busy, setBusy] = useState(false); const [result, setResult] = useState(null);
  const [camOn, setCamOn] = useState(false); const [guest, setGuest] = useState(false); const [guestForm, setGuestForm] = useState({ name: "", origin: "", purpose: "Membaca" });
  const [filter, setFilter] = useState("semua"); const [cfgOpen, setCfgOpen] = useState(false); const [cfgTime, setCfgTime] = useState("14:00");
  const inputRef = useRef(null); const kioskRef = useRef(null); const resultTimer = useRef(null);
  const isToday = date === todayStr();
  const load = useCallback(() => api.get("/visits", { params: { date } }).then((r) => setData(r.data)).catch(() => notify("Data pengunjung belum dapat dimuat")), [date]);
  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (isToday) inputRef.current?.focus(); }, [isToday]);
  const flash = (r) => { setResult(r); clearTimeout(resultTimer.current); resultTimer.current = setTimeout(() => setResult(null), 6000); };
  const [members, setMembers] = useState([]); const [hi, setHi] = useState(0); const [sugOpen, setSugOpen] = useState(false);
  useEffect(() => { api.get("/members/options").then((r) => setMembers(r.data)).catch(() => {}); }, []);
  const q = code.trim().toLowerCase();
  const suggestions = q.length >= 2 ? members.filter((m) => m.name.toLowerCase().includes(q) || (m.student_id || "").toLowerCase().startsWith(q) || m.id.toLowerCase() === q).slice(0, 8) : [];
  const looksLikeCode = (v) => /^mb-/i.test(v.trim()) || /^\d+$/.test(v.trim());
  const busyRef = useRef(false);
  const submitCode = async (raw) => {
    const c = (raw || "").trim(); if (!c || busyRef.current) return null;
    busyRef.current = true; setBusy(true); setSugOpen(false);
    try {
      const { data: r } = await api.post("/visits/scan", { code: c });
      beep(r.action === "masuk" || r.action === "keluar"); flash(r); load();
      const name = r.member?.name || "Pengunjung";
      if (r.action === "masuk") { notify(`Pengunjung tercatat · ${name}`); return { ok: true, title: name, sub: "Berhasil · tercatat masuk" }; }
      if (r.action === "keluar") { notify(`${name} tercatat keluar`); return { ok: true, title: name, sub: "Berhasil · tercatat keluar" }; }
      return { ok: true, title: name, sub: r.action === "sudah_masuk" ? "Sudah tercatat masuk" : "Sudah tercatat keluar" };
    } catch (e) { beep(false); const msg = e.response?.data?.detail || "Gagal memproses kode"; flash({ action: "error", message: msg }); return { ok: false, title: "Gagal", sub: msg }; }
    finally { busyRef.current = false; setBusy(false); setCode(""); setHi(0); inputRef.current?.focus(); }
  };
  const onCodeKey = (e) => {
    if (!suggestions.length || !sugOpen) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => (h + 1) % suggestions.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => (h - 1 + suggestions.length) % suggestions.length); }
    else if (e.key === "Escape") setSugOpen(false);
  };
  const submitForm = (e) => { e.preventDefault(); if (sugOpen && suggestions.length && !looksLikeCode(code)) submitCode(suggestions[Math.min(hi, suggestions.length - 1)].id); else submitCode(code); };
  const addGuest = async (e) => {
    e.preventDefault();
    try { const { data: v } = await api.post("/visits/guest", guestForm); setGuest(false); setGuestForm({ name: "", origin: "", purpose: "Membaca" }); flash({ action: "masuk", visit: v, member: { name: v.name, class_name: v.origin || "Tamu" } }); load(); }
    catch (err) { notify(err.response?.data?.detail || "Gagal mencatat tamu"); }
  };
  const checkout = async (v) => { try { await api.post(`/visits/${v.id}/checkout`); notify(`${v.name} tercatat keluar`); load(); } catch (e) { notify(e.response?.data?.detail || "Gagal"); } };
  const remove = async (v) => { if (!window.confirm(`Hapus catatan pengunjung ${v.name}?`)) return; try { await api.delete(`/visits/${v.id}`); notify("Catatan pengunjung dihapus"); load(); } catch (e) { notify("Gagal menghapus"); } };
  const saveCfg = async (e) => { e.preventDefault(); try { const { data: r } = await api.put("/visits/config", { checkout_time: cfgTime }); setCfgOpen(false); notify(`Otomatis keluar diatur pukul ${r.checkout_time} WIB`); load(); } catch (err) { notify("Format jam tidak valid"); } };
  const fullscreen = () => { const el = kioskRef.current; if (!el) return; if (document.fullscreenElement) document.exitFullscreen(); else el.requestFullscreen?.(); };
  const rows = data.items.filter((v) => filter === "semua" || (filter === "dalam" ? !v.check_out : !!v.check_out));
  const s = data.summary;
  const res = result;
  return <div className="visitors-page" data-testid="visitors-page">
    <div className="visit-top">
      <section className="panel visit-kiosk" ref={kioskRef} data-testid="visit-kiosk">
        <div className="panel-title"><div><p className="eyebrow">BUKU TAMU DIGITAL</p><h3>Scan kartu saat masuk &amp; keluar</h3></div><button className="icon-button" title="Layar penuh" data-testid="visit-fullscreen-button" onClick={fullscreen}><Maximize2 size={17}/></button></div>
        <div className="visit-kiosk-body">
          <div className="visit-scan-area">
            {camOn ? <LiveScanner onCode={submitCode}/> : <div className="visit-scan-idle"><ScanLine size={44}/><b>Siap memindai</b><span>Arahkan alat pemindai QR ke kartu anggota, atau nyalakan kamera.</span></div>}
            <button className={camOn ? "secondary full" : "primary full"} data-testid="visit-camera-toggle" onClick={() => setCamOn(!camOn)}>{camOn ? <><CameraOff size={16}/> Matikan kamera</> : <><Camera size={16}/> Nyalakan kamera</>}</button>
          </div>
          <div className="visit-scan-side">
            <form className="visit-code-form" onSubmit={submitForm}>
              <label className="visit-search-label">Kode kartu / NIS / Nama
                <input ref={inputRef} data-testid="visit-code-input" placeholder="Scan, ketik kode, atau cari nama" value={code} onChange={(e) => { setCode(e.target.value); setHi(0); setSugOpen(true); }} onKeyDown={onCodeKey} onBlur={() => setTimeout(() => setSugOpen(false), 150)} onFocus={() => setSugOpen(true)} disabled={!isToday} autoComplete="off"/>
                {sugOpen && suggestions.length > 0 && <ul className="visit-suggest" data-testid="visit-name-suggestions" role="listbox">{suggestions.map((m, i) => <li key={m.id} role="option" aria-selected={i === hi}><button type="button" className={i === hi ? "active" : ""} data-testid={`visit-suggest-${m.id}`} onMouseDown={(e) => e.preventDefault()} onClick={() => submitCode(m.id)} onMouseEnter={() => setHi(i)}>
                  <span className="sug-avatar">{m.photo ? <img src={m.photo} alt=""/> : m.name[0]}</span><span className="sug-text"><b>{m.name}</b><small>{m.class_name} · NIS {m.student_id}</small></span><LogIn size={14}/>
                </button></li>)}</ul>}
                {sugOpen && q.length >= 2 && !suggestions.length && !looksLikeCode(code) && <div className="visit-suggest empty" data-testid="visit-name-no-result">Nama tidak ditemukan</div>}
              </label>
              <button className="primary" data-testid="visit-code-submit" disabled={busy || !isToday}><LogIn size={16}/> {busy ? "Memproses..." : "Catat"}</button>
            </form>
            <div className={`visit-result ${res ? res.action : "idle"}`} data-testid="visit-result" aria-live="polite">
              {!res && <><Users size={22}/><div><b>Scan pertama = masuk, scan berikutnya = keluar</b><span>Yang lupa scan keluar otomatis tercatat keluar pukul {data.checkout_time} WIB.</span></div></>}
              {res?.action === "masuk" && <><DoorOpen size={26}/><div><small>MASUK · {fmtClock(res.visit?.check_in)}</small><b data-testid="visit-result-name">{res.member?.name}</b><span>Selamat datang{res.member?.class_name ? ` · ${res.member.class_name}` : ""}</span></div></>}
              {res?.action === "keluar" && <><DoorClosed size={26}/><div><small>KELUAR · {fmtClock(res.visit?.check_out)}</small><b data-testid="visit-result-name">{res.member?.name}</b><span>Sampai jumpa · lama berkunjung {fmtDur(res.visit?.duration_min)}</span></div></>}
              {(res?.action === "sudah_masuk" || res?.action === "sudah_keluar") && <><Clock size={24}/><div><small>BARU SAJA DIPINDAI</small><b data-testid="visit-result-name">{res.member?.name}</b><span>{res.action === "sudah_masuk" ? "Sudah tercatat masuk. Scan lagi saat keluar." : "Sudah tercatat keluar."}</span></div></>}
              {res?.action === "error" && <><ScanLine size={24}/><div><small>GAGAL</small><b data-testid="visit-result-name">{res.message}</b><span>Periksa kartu atau catat sebagai tamu.</span></div></>}
            </div>
            <button className="secondary full" data-testid="visit-guest-button" onClick={() => setGuest(true)} disabled={!isToday}><UserPlus size={16}/> Catat tamu (tanpa kartu)</button>
          </div>
        </div>
      </section>
      <aside className="visit-stats">
        <div className="visit-stat big" data-testid="visit-inside"><span>Di dalam sekarang</span><strong>{s.inside}</strong><small>pengunjung</small></div>
        <div className="visit-stat" data-testid="visit-total"><span>{isToday ? "Total hari ini" : "Total tanggal ini"}</span><strong>{s.total}</strong></div>
        <div className="visit-stat"><span>Anggota</span><strong data-testid="visit-members-count">{s.anggota}</strong><small>{s.total ? Math.round((s.anggota / s.total) * 100) : 0}%</small></div>
        <div className="visit-stat"><span>Tamu</span><strong data-testid="visit-guests-count">{s.tamu}</strong><small>{s.total ? Math.round((s.tamu / s.total) * 100) : 0}%</small></div>
        <button className="visit-auto" data-testid="visit-config-button" onClick={() => { setCfgTime(data.checkout_time); setCfgOpen(true); }}><Clock size={16}/><div><b>Otomatis keluar {data.checkout_time} WIB</b><small>Ubah jam pulang sekolah</small></div><Pencil size={14}/></button>
      </aside>
    </div>
    <div className="panel table-panel">
      <div className="panel-title visit-list-head"><div><p className="eyebrow">DAFTAR PENGUNJUNG</p><h3>{rows.length} catatan</h3></div>
        <div className="visit-filters">
          <div className="period-select">{[["semua", "Semua"], ["dalam", "Di dalam"], ["keluar", "Sudah keluar"]].map(([k, l]) => <button key={k} data-testid={`visit-filter-${k}`} className={filter === k ? "active" : ""} onClick={() => setFilter(k)}>{l}</button>)}</div>
          <input type="date" data-testid="visit-date-input" value={date} max={todayStr()} onChange={(e) => setDate(e.target.value || todayStr())}/>
        </div>
      </div>
      <div className="table-wrap"><table><thead><tr><th>PENGUNJUNG</th><th>KELAS / ASAL</th><th>MASUK</th><th>KELUAR</th><th>DURASI</th><th>STATUS</th><th></th></tr></thead><tbody>
        {rows.map((v) => <tr key={v.id} data-testid={`visit-row-${v.id}`}>
          <td><div className="book-cell"><div className={`avatar ${v.kind === "tamu" ? "guest" : ""}`}>{v.photo ? <img src={v.photo} alt={v.name}/> : v.name[0]}</div><div><b>{v.name}</b><span>{v.kind === "tamu" ? `Tamu${v.purpose ? ` · ${v.purpose}` : ""}` : `Anggota · ${v.student_id || v.member_id}`}</span></div></div></td>
          <td>{v.kind === "tamu" ? (v.origin || "-") : v.class_name}</td>
          <td>{fmtClock(v.check_in)}</td>
          <td>{v.check_out ? fmtClock(v.check_out) : "-"}</td>
          <td>{fmtDur(v.duration_min)}</td>
          <td>{v.check_out ? <span className={`status ${v.checkout_type === "otomatis" ? "dipinjam" : "keluar"}`}>{OUT_LABEL[v.checkout_type] || "Keluar"}</span> : <span className="status tersedia" data-testid={`visit-inside-${v.id}`}>Di dalam</span>}</td>
          <td><div className="row-actions">{!v.check_out && <button className="ok-icon" title="Catat keluar" data-testid={`visit-checkout-${v.id}`} onClick={() => checkout(v)}><LogOut size={15}/></button>}<button className="danger-icon" title="Hapus" data-testid={`visit-delete-${v.id}`} onClick={() => remove(v)}><Trash2 size={15}/></button></div></td>
        </tr>)}
        {rows.length === 0 && <tr><td colSpan={7} style={{ textAlign: "center", padding: 30, color: "#94a3b8" }} data-testid="visit-empty">Belum ada pengunjung pada tanggal ini</td></tr>}
      </tbody></table></div>
    </div>
    {guest && <Modal title="Catat tamu" close={() => setGuest(false)}><form className="modal-form" onSubmit={addGuest} data-testid="guest-form">
      <label>Nama tamu<input data-testid="guest-name-input" required value={guestForm.name} onChange={(e) => setGuestForm({ ...guestForm, name: e.target.value })}/></label>
      <label>Asal / instansi<input data-testid="guest-origin-input" placeholder="mis. Guru, Orang tua, Dinas Pendidikan" value={guestForm.origin} onChange={(e) => setGuestForm({ ...guestForm, origin: e.target.value })}/></label>
      <label>Keperluan<select data-testid="guest-purpose-input" value={guestForm.purpose} onChange={(e) => setGuestForm({ ...guestForm, purpose: e.target.value })}><option>Membaca</option><option>Meminjam / mengembalikan buku</option><option>Mengerjakan tugas</option><option>Kunjungan dinas</option><option>Lainnya</option></select></label>
      <button className="primary full" data-testid="save-guest-button"><UserPlus size={16}/> Catat masuk</button>
    </form></Modal>}
    {cfgOpen && <Modal title="Jam otomatis keluar" close={() => setCfgOpen(false)}><form className="modal-form" onSubmit={saveCfg}>
      <p className="account-hint" style={{ marginTop: 0 }}>Pengunjung yang belum scan keluar akan otomatis tercatat keluar pada jam ini (WIB). Yang masuk setelah jam ini ditutup pada akhir hari.</p>
      <label>Jam pulang sekolah<input type="time" data-testid="visit-config-time-input" required value={cfgTime} onChange={(e) => setCfgTime(e.target.value)}/></label>
      <button className="primary full" data-testid="save-visit-config-button">Simpan</button>
    </form></Modal>}
  </div>;
}
