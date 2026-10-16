import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Camera, CameraOff, CheckCircle2, Clock, DoorClosed, DoorOpen, LogIn, LogOut, ShieldAlert, UserCheck, Users, X } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";
import { CameraScanner } from "./CameraScanner";
import { beep, cameraError, createCamera, unlockAudio } from "../lib/camera";

const COOLDOWN_MS = 1000;
const todayStr = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);
export const fmtClock = (d) => d ? new Date(d).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }) : "-";
export const fmtDur = (m) => m == null ? "-" : m >= 60 ? `${Math.floor(m / 60)} j ${m % 60} m` : `${m} menit`;
export const OUT_LABEL = { scan: "Scan keluar", manual: "Dicatat petugas", otomatis: "Otomatis" };

const OVERLAY = {
  masuk: { tone: "ok", label: "BERHASIL · MASUK", Icon: CheckCircle2 },
  keluar: { tone: "ok", label: "BERHASIL · KELUAR", Icon: CheckCircle2 },
  sudah_masuk: { tone: "warn", label: "SUDAH TERCATAT MASUK", Icon: Clock },
  sudah_keluar: { tone: "warn", label: "SUDAH TERCATAT KELUAR", Icon: Clock },
  error: { tone: "bad", label: "GAGAL", Icon: AlertTriangle },
};

function LiveScanner({ onCode }) {
 fitur/laporan-kartu-belakang-cetak-duplex
  return <div className="visit-cam" data-testid="visit-camera"><CameraScanner onCode={onCode} testId="visit-camera-scanner"/></div>;

  const [err, setErr] = useState(""); const [ready, setReady] = useState(false); const [hit, setHit] = useState(null);
  const lock = useRef(false); const last = useRef({ code: "", at: 0 }); const cb = useRef(onCode); const timer = useRef(null); const boxRef = useRef(null);
  cb.current = onCode;
  useEffect(() => {
    let alive = true; let cam = null;
    const onDecode = async (text) => {
      const now = Date.now();
      // Kartu yang sama masih di depan kamera: abaikan sebentar agar tidak langsung tercatat keluar
      if (lock.current || (text === last.current.code && now - last.current.at < 5000)) return;
      lock.current = true; last.current = { code: text, at: now };
      let r;
      try { r = await cb.current(text); } catch (e) { r = null; }
      if (!alive) return;
      setHit(r || { action: "error", message: "Gagal memproses kode" });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => { if (!alive) return; setHit(null); lock.current = false; last.current.at = Date.now(); }, COOLDOWN_MS);
    };
    // Ditunda sedikit agar kamera hanya dibuka sekali (React dev memasang komponen dua kali)
    const t = setTimeout(() => {
      if (!alive || !boxRef.current) return;
      cam = createCamera(boxRef.current);
      cam.start(onDecode).then(() => alive && setReady(true)).catch((e) => alive && setErr(cameraError(e)));
    }, 60);
    return () => { alive = false; clearTimeout(t); clearTimeout(timer.current); cam?.stop(); };
  }, []);
  const o = hit ? (OVERLAY[hit.action] || OVERLAY.error) : null;
  return <div className="visit-cam" data-testid="visit-camera">
    <div className="visit-cam-frame">
      <div ref={boxRef} className="visit-qr-reader"/>
      {o && <div className={`visit-cam-hit ${o.tone}`} data-testid="visit-camera-hit">
        <o.Icon size={46}/>
        <small>{o.label}</small>
        <b>{hit.member?.name || hit.message}</b>
        <span>{o.tone === "bad" ? "Periksa kartu lalu scan lagi" : hit.member?.class_name || "Tamu"}</span>
        <i className="visit-cam-bar" style={{ animationDuration: `${COOLDOWN_MS}ms` }}/>
      </div>}
    </div>
    {!err && <div className={`visit-cam-status ${hit ? "wait" : ready ? "ready" : ""}`} data-testid="visit-camera-status">
      <span className="dot"/>{!ready ? "Membuka kamera..." : hit ? "Tunggu sebentar..." : "Siap scan — arahkan QR kartu ke kotak"}
    </div>}
    {err && <div className="error" data-testid="visit-camera-error">{err}</div>}
  </div>;
 main
}

function MemberSuggest({ items, active, onPick }) {
  if (!items.length) return null;
  return <ul className="visit-suggest" data-testid="visit-suggest" role="listbox">
    {items.map((m, i) => <li key={m.id}>
      <button type="button" role="option" aria-selected={i === active} className={i === active ? "active" : ""} data-testid={`visit-suggest-${m.id}`} onMouseDown={(e) => e.preventDefault()} onClick={() => onPick(m)}>
        <div className="avatar">{m.photo ? <img src={m.photo} alt={m.name}/> : (m.name || "?")[0]}</div>
        <div className="visit-suggest-text"><b>{m.name}</b><span>{m.class_name || "-"} · NIS {m.student_id || m.id}</span></div>
        <em className={m.inside ? "out" : "in"}>{m.inside ? <><LogOut size={13}/> Catat keluar</> : <><LogIn size={13}/> Catat masuk</>}</em>
      </button>
    </li>)}
  </ul>;
}

export function Visitors({ notify }) {
  const [date, setDate] = useState(todayStr()); const [data, setData] = useState({ items: [], summary: { total: 0, inside: 0, anggota: 0, tamu: 0 }, checkout_time: "14:00" });
  const [code, setCode] = useState(""); const [busy, setBusy] = useState(false); const [result, setResult] = useState(null);
  const [camOn, setCamOn] = useState(false); const [guest, setGuest] = useState(false); const [guestForm, setGuestForm] = useState({ name: "", origin: "", purpose: "Membaca" });
  const [filter, setFilter] = useState("semua"); const [cfgOpen, setCfgOpen] = useState(false); const [cfgTime, setCfgTime] = useState("14:00");
  const [q, setQ] = useState(""); const [sugs, setSugs] = useState([]); const [sugActive, setSugActive] = useState(-1);
  const inputRef = useRef(null); const kioskRef = useRef(null); const resultTimer = useRef(null); const camOnRef = useRef(false); const busyRef = useRef(false);
  camOnRef.current = camOn;
  const isToday = date === todayStr();
  const notifyRef = useRef(notify); notifyRef.current = notify;
  const load = useCallback(() => api.get("/visits", { params: { date } }).then((r) => setData(r.data)).catch(() => notifyRef.current("Data pengunjung belum dapat dimuat")), [date]);
  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (isToday && !camOnRef.current) inputRef.current?.focus(); }, [isToday]);
  // Saran nama anggota saat mengetik di kolom pencarian
  useEffect(() => {
    const term = code.trim();
    if (term.length < 2) { setSugs([]); setSugActive(-1); return undefined; }
    let live = true;
    const t = setTimeout(() => {
      api.get("/visits/member-search", { params: { q: term } }).then((r) => { if (live) { setSugs(r.data); setSugActive(-1); } }).catch(() => live && setSugs([]));
    }, 200);
    return () => { live = false; clearTimeout(t); };
  }, [code]);
  const flash = (r) => { setResult(r); clearTimeout(resultTimer.current); resultTimer.current = setTimeout(() => setResult(null), 6000); };
  const [members, setMembers] = useState([]); const [hi, setHi] = useState(0); const [sugOpen, setSugOpen] = useState(false);
  useEffect(() => { api.get("/members/options").then((r) => setMembers(r.data)).catch(() => {}); }, []);
  const q = code.trim().toLowerCase();
  const suggestions = q.length >= 2 ? members.filter((m) => m.name.toLowerCase().includes(q) || (m.student_id || "").toLowerCase().startsWith(q) || m.id.toLowerCase() === q).slice(0, 8) : [];
  const looksLikeCode = (v) => /^mb-/i.test(v.trim()) || /^\d+$/.test(v.trim());
  const busyRef = useRef(false);
  const submitCode = async (raw) => {
    const c = (raw || "").trim(); if (!c || busyRef.current) return null;
 fitur/laporan-kartu-belakang-cetak-duplex
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

    busyRef.current = true; setBusy(true);
    let out = null;
    try {
      const { data: r } = await api.post("/visits/scan", { code: c });
      beep(r.action === "masuk" || r.action === "keluar"); flash(r); load(); out = r;
    } catch (e) { beep(false); out = { action: "error", message: e.response?.data?.detail || "Gagal memproses kode" }; flash(out); }
    finally {
      busyRef.current = false; setBusy(false); setCode(""); setSugs([]); setSugActive(-1);
      // Di HP jangan fokus ke kolom ketik saat kamera aktif (keyboard akan menutupi kamera)
      if (!camOnRef.current) inputRef.current?.focus();
    }
    return out;
  };
  const pickMember = (m) => submitCode(m.id);
  const onSearchSubmit = (e) => {
    e.preventDefault();
    if (sugActive >= 0 && sugs[sugActive]) return pickMember(sugs[sugActive]);
    const t = code.trim().toLowerCase();
    const exact = sugs.find((m) => (m.id || "").toLowerCase() === t || (m.student_id || "").toLowerCase() === t);
    if (!exact && sugs.length === 1) return pickMember(sugs[0]);
    return submitCode(code);
  };
  const onSearchKey = (e) => {
    if (!sugs.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setSugActive((i) => (i + 1) % sugs.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSugActive((i) => (i <= 0 ? sugs.length - 1 : i - 1)); }
    else if (e.key === "Escape") { e.stopPropagation(); setSugs([]); setSugActive(-1); }
 main
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
  const term = q.trim().toLowerCase();
  const rows = data.items.filter((v) => filter === "semua" || (filter === "dalam" ? !v.check_out : !!v.check_out))
    .filter((v) => !term || [v.name, v.class_name, v.origin, v.student_id, v.member_id, v.purpose].some((x) => (x || "").toLowerCase().includes(term)));
  const s = data.summary;
  const res = result;
  return <div className="visitors-page" data-testid="visitors-page">
    <div className="visit-top">
      <section className="panel visit-kiosk" ref={kioskRef} data-testid="visit-kiosk">
        <div className="panel-title"><div><p className="eyebrow">BUKU TAMU DIGITAL</p><h3>Scan kartu saat masuk &amp; keluar</h3></div><button className="icon-button" title="Layar penuh" data-testid="visit-fullscreen-button" onClick={fullscreen}><Maximize2 size={17}/></button></div>
        <div className="visit-kiosk-body">
          <div className="visit-scan-area">
            {camOn ? <LiveScanner onCode={submitCode}/> : <div className="visit-scan-idle"><ScanLine size={44}/><b>Siap memindai</b><span>Arahkan alat pemindai QR ke kartu anggota, atau nyalakan kamera.</span></div>}
 fitur/laporan-kartu-belakang-cetak-duplex
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

            <button className={camOn ? "secondary full" : "primary full"} data-testid="visit-camera-toggle" onClick={() => { unlockAudio(); setCamOn(!camOn); }} disabled={!isToday}>{camOn ? <><CameraOff size={16}/> Matikan kamera</> : <><Camera size={16}/> Nyalakan kamera</>}</button>
          </div>
          <div className="visit-scan-side">
            <form className="visit-code-form" onSubmit={onSearchSubmit} autoComplete="off">
              <div className="visit-search-wrap">
                <label>Nama siswa / kode kartu / NIS<div className="visit-search-input"><Search size={16}/><input ref={inputRef} data-testid="visit-code-input" placeholder="Ketik nama, atau scan kartu lalu Enter" value={code} onChange={(e) => setCode(e.target.value)} onKeyDown={onSearchKey} onBlur={() => setTimeout(() => setSugs([]), 150)} disabled={!isToday} autoComplete="off"/>{code && <button type="button" className="visit-search-clear" aria-label="Hapus" data-testid="visit-code-clear" onClick={() => { setCode(""); inputRef.current?.focus(); }}><X size={14}/></button>}</div></label>
                <MemberSuggest items={sugs} active={sugActive} onPick={pickMember}/>
              </div>
 main
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
          <div className="visit-list-search"><Search size={15}/><input data-testid="visit-list-search" placeholder="Cari nama pengunjung..." value={q} onChange={(e) => setQ(e.target.value)}/>{q && <button type="button" aria-label="Hapus pencarian" data-testid="visit-list-search-clear" onClick={() => setQ("")}><X size={13}/></button>}</div>
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
        {rows.length === 0 && <tr><td colSpan={7} style={{ textAlign: "center", padding: 30, color: "#94a3b8" }} data-testid="visit-empty">{term ? `Tidak ada pengunjung bernama "${q.trim()}"` : "Belum ada pengunjung pada tanggal ini"}</td></tr>}
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
