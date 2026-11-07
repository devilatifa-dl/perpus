// Peringkat Siswa / Guru dihitung di browser.
//
// Backend produksi (Emergent) belum mendukung parameter `audience`, sehingga tab "Guru"
// menampilkan data siswa. Modul ini mereplikasi perhitungan backend (visits.py & loan_rank.py)
// memakai data mentah yang sudah tersedia: /members, /visits/history, /transactions.
// Begitu backend mendukung `audience`, hasilnya identik karena rumus & urutannya sama.

const MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const WIB_OFFSET_MS = 7 * 60 * 60 * 1000;

export const normAudience = (a) => ((a || "siswa").trim().toLowerCase() === "guru" ? "guru" : "siswa");

/** Tanggal ISO (UTC) -> { month: "YYYY-MM", day: "YYYY-MM-DD" } dalam zona WIB. */
function wibParts(value) {
  if (!value) return { month: "", day: "" };
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) {
    const s = String(value);
    return { month: s.slice(0, 7), day: s.slice(0, 10) };
  }
  const wib = new Date(dt.getTime() + WIB_OFFSET_MS);
  const y = wib.getUTCFullYear();
  const m = String(wib.getUTCMonth() + 1).padStart(2, "0");
  const d = String(wib.getUTCDate()).padStart(2, "0");
  return { month: `${y}-${m}`, day: `${y}-${d}` };
}

/** Bulan berjalan (WIB) dalam format YYYY-MM. */
export function currentMonthWib() {
  const wib = new Date(Date.now() + WIB_OFFSET_MS);
  return `${wib.getUTCFullYear()}-${String(wib.getUTCMonth() + 1).padStart(2, "0")}`;
}

/** Label bulan Indonesia, mis. "November 2026". */
export function monthLabel(key) {
  const [y, m] = String(key || "").split("-").map(Number);
  if (!y || !m || m < 1 || m > 12) return key || "-";
  return `${MONTHS_ID[m - 1]} ${y}`;
}

/** Himpunan id anggota bertipe guru. */
export function guruIdSet(members) {
  return new Set((members || []).filter((m) => (m?.member_type || "siswa") === "guru").map((m) => m.id));
}

/** Baris milik guru: anggotanya bertipe guru, atau kelas tercatat "Guru" (riwayat lama). */
export function isGuruRow(row, guruIds) {
  if (!row) return false;
  if (guruIds.has(row.member_id)) return true;
  return String(row.class_name || "").trim().toLowerCase() === "guru";
}

const pct = (n, total) => (total ? Math.round((n * 100 * 10) / total) / 10 : 0);

/**
 * Peringkat kunjungan (replika visit_leaderboard).
 * @param {object} p
 * @param {Array} p.visits  hasil /visits/history (semua periode)
 * @param {Array} p.members daftar anggota
 * @param {string} p.month  YYYY-MM
 * @param {string} p.audience "siswa" | "guru"
 * @param {number} p.limit
 */
export function visitLeaderboard({ visits = [], members = [], month, audience = "siswa", limit = 10 }) {
  const aud = normAudience(audience);
  const key = month || currentMonthWib();
  const guruIds = guruIdSet(members);
  const rows = (visits || []).filter(
    (r) => r?.kind === "anggota" && String(r.date || "").startsWith(key) && isGuruRow(r, guruIds) === (aud === "guru")
  );

  const students = new Map();
  const classes = new Map();
  for (const r of rows) {
    const mid = r.member_id || r.name;
    let st = students.get(mid);
    if (!st) {
      st = { member_id: r.member_id, name: r.name || "-", class_name: r.class_name || "-", visits: 0, days: new Set(), minutes: 0 };
      students.set(mid, st);
    }
    st.visits += 1;
    st.days.add(r.date);
    st.minutes += Number(r.duration_min) || 0;

    const cls = String(r.class_name || "").trim() || "Tanpa kelas";
    let c = classes.get(cls);
    if (!c) {
      c = { class_name: cls, visits: 0, members: new Set() };
      classes.set(cls, c);
    }
    c.visits += 1;
    c.members.add(mid);
  }

  const byId = new Map((members || []).map((m) => [m.id, m]));
  const total = rows.length;
  const ranked = [...students.values()].sort(
    (a, b) => b.visits - a.visits || b.days.size - a.days.size || b.minutes - a.minutes || a.name.localeCompare(b.name, "id")
  );

  const outStudents = ranked.slice(0, limit).map((st, i) => {
    const mem = byId.get(st.member_id) || {};
    return {
      rank: i + 1,
      member_id: st.member_id,
      name: mem.name || st.name,
      class_name: mem.class_name || st.class_name,
      photo: mem.photo || "",
      visits: st.visits,
      days: st.days.size,
      minutes: st.minutes,
      pct: pct(st.visits, total),
    };
  });

  const outClasses =
    aud === "guru"
      ? []
      : [...classes.values()]
          .sort((a, b) => b.visits - a.visits || b.members.size - a.members.size || a.class_name.localeCompare(b.class_name, "id"))
          .map((c, i) => ({ rank: i + 1, class_name: c.class_name, visits: c.visits, members: c.members.size, pct: pct(c.visits, total) }));

  const months = [...new Set([...(visits || []).filter((v) => v?.kind === "anggota" && v.date).map((v) => String(v.date).slice(0, 7)), currentMonthWib()])].sort().reverse();

  return {
    month: key,
    label: monthLabel(key),
    audience: aud,
    total_visits: total,
    active_students: students.size,
    students: outStudents,
    classes: outClasses,
    months,
  };
}

/**
 * Peringkat peminjaman (replika loan_leaderboard).
 * @param {object} p
 * @param {Array} p.transactions hasil /transactions
 * @param {Array} p.members
 * @param {string} p.month
 * @param {string} p.audience
 * @param {number} p.limit
 */
export function loanLeaderboard({ transactions = [], members = [], month, audience = "siswa", limit = 10 }) {
  const aud = normAudience(audience);
  const key = month || currentMonthWib();
  const guruIds = guruIdSet(members);
  const allLoans = (transactions || []).filter((t) => t?.action === "pinjam");
  const rows = allLoans.filter((t) => wibParts(t.date).month === key && isGuruRow(t, guruIds) === (aud === "guru"));

  const byId = new Map((members || []).map((m) => [m.id, m]));
  const students = new Map();
  const classes = new Map();

  for (const t of rows) {
    const mid = t.member_id || t.member_name;
    const mem = byId.get(t.member_id) || {};
    const clsName = String(t.class_name || mem.class_name || "").trim();

    let st = students.get(mid);
    if (!st) {
      st = { member_id: t.member_id, name: t.member_name || "-", class_name: clsName || "-", loans: 0, books: new Set(), days: new Set() };
      students.set(mid, st);
    }
    st.loans += 1;
    st.books.add(t.book_title || t.book_id);
    st.days.add(wibParts(t.date).day);

    const cls = clsName || "Tanpa kelas";
    let c = classes.get(cls);
    if (!c) {
      c = { class_name: cls, loans: 0, members: new Set() };
      classes.set(cls, c);
    }
    c.loans += 1;
    c.members.add(mid);
  }

  const total = rows.length;
  const ranked = [...students.values()].sort(
    (a, b) => b.loans - a.loans || b.books.size - a.books.size || b.days.size - a.days.size || a.name.localeCompare(b.name, "id")
  );

  const outStudents = ranked.slice(0, limit).map((st, i) => {
    const mem = byId.get(st.member_id) || {};
    return {
      rank: i + 1,
      member_id: st.member_id,
      name: mem.name || st.name,
      class_name: mem.class_name || st.class_name,
      photo: mem.photo || "",
      loans: st.loans,
      books: st.books.size,
      days: st.days.size,
      pct: pct(st.loans, total),
    };
  });

  const outClasses =
    aud === "guru"
      ? []
      : [...classes.values()]
          .sort((a, b) => b.loans - a.loans || b.members.size - a.members.size || a.class_name.localeCompare(b.class_name, "id"))
          .map((c, i) => ({ rank: i + 1, class_name: c.class_name, loans: c.loans, members: c.members.size, pct: pct(c.loans, total) }));

  const months = [...new Set([...allLoans.map((t) => wibParts(t.date).month).filter(Boolean), currentMonthWib()])].sort().reverse();

  return {
    month: key,
    label: monthLabel(key),
    audience: aud,
    total_loans: total,
    active_students: students.size,
    students: outStudents,
    classes: outClasses,
    months,
  };
}
