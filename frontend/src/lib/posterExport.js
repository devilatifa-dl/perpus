// Poster digital peringkat (Rajin Berkunjung / Rajin Meminjam).
// Dua ukuran: A4 portrait (2480 x 3507 px, 300 DPI) dan Story 9:16 (2160 x 3840 px) untuk Instagram/WhatsApp.
// Digambar langsung di <canvas> dari data peringkat yang sedang tampil di Laporan.
import { api, SCHOOL_LOGO, LIBRARY_LOGO } from "../lib";
import { withPngDpi, saveBlob } from "./cardExport";

export const LIBRARY_LABEL = "PERPUSTAKAAN";
export const POSTER_SLOGAN = "BUDAYAKAN MEMBACA, PERLUAS WAWASAN";
const BG_URL = "/poster/library-bg.jpg";
const W = 1000; // lebar satuan desain; dikali scale saat digambar
const HEAD = '"Exo 2", "Outfit", "Plus Jakarta Sans", sans-serif';
const BODY = '"Plus Jakarta Sans", "Inter", sans-serif';
const C = {
  navy: "#0b1d45", deep: "#050f29", mid: "#13306b", gold: "#d4a537", goldL: "#f7dc84", goldD: "#9a6f17",
  white: "#ffffff", soft: "#cfd9ec", muted: "#8ea0c4",
};
const MEDALS = [
  { a: "#fff1b0", b: "#e2b33c", c: "#9a6f17", label: "EMAS" },
  { a: "#ffffff", b: "#c3ccd8", c: "#6f7b8d", label: "PERAK" },
  { a: "#ffd2a6", b: "#cd8544", c: "#7c4316", label: "PERUNGGU" },
];

// ===== Ukuran poster =====
// Semua posisi dalam satuan desain (lebar 1000). Kop dibuat rapat ke tepi atas (tanpa ruang kosong berlebih).
export const POSTER_FORMATS = {
  a4: {
    id: "a4", label: "A4", H: 1414, scale: 2.48, dpi: 300, suffix: "a4",
    hy: 82, logoR: 50, ty: 200, t1: 74, t2: 104,
    pb: 886, ph: [126, 104, 90], ar: [66, 56, 56], colW: 250,
    tbY: 898, rowH: 35.5, sY: 1246, sH: 86, bY: 1354,
  },
  story: {
    id: "story", label: "Story 9:16", H: 1778, scale: 2.16, dpi: 300, suffix: "story",
    hy: 112, logoR: 56, ty: 244, t1: 80, t2: 112,
    pb: 1052, ph: [156, 116, 88], ar: [78, 66, 66], colW: 262,
    tbY: 1078, rowH: 48, sY: 1518, sH: 110, bY: 1648,
  },
};

// ===== Jenis peringkat =====
export function fmtDuration(min, short = false) {
  const t = Math.max(0, Math.round(Number(min) || 0));
  const h = Math.floor(t / 60), m = t % 60;
  if (short) return h ? `${h} jam ${m} mnt` : `${m} mnt`;
  return h ? `${h} jam ${m} menit` : `${m} menit`;
}
const num = (v) => new Intl.NumberFormat("id-ID").format(v || 0);
const pctText = (p) => `${String(p ?? 0).replace(".", ",")}%`;

const KINDS = {
  kunjungan: {
    title2: "BERKUNJUNG", file: "berkunjung", total: "total_visits", icon: "clock",
    pill: (s) => fmtDuration(s.minutes),
    colHead: "TOTAL WAKTU", col: (s) => fmtDuration(s.minutes, true),
    statTotal: "TOTAL PENGUNJUNG", statClass: "KELAS TERAKTIF", statPct: "PENGUNJUNG KELAS TERAKTIF",
    guruSum: (list) => ({ label: "TOTAL WAKTU 10 BESAR", value: fmtDuration(list.reduce((a, s) => a + (Number(s.minutes) || 0), 0), true) }),
  },
  pinjam: {
    title2: "MEMINJAM", file: "meminjam", total: "total_loans", icon: "book",
    pill: (s) => `${num(s.loans)} buku · ${num(s.books)} judul`,
    colHead: "BUKU DIPINJAM", col: (s) => `${num(s.loans)} buku`,
    statTotal: "TOTAL PEMINJAMAN", statClass: "KELAS TERAJIN", statPct: "PEMINJAMAN KELAS TERAJIN",
    guruSum: (list) => ({ label: "BUKU DIPINJAM 10 BESAR", value: `${num(list.reduce((a, s) => a + (Number(s.loans) || 0), 0))} buku` }),
  },
};

const initials = (n = "") => n.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";

function loadImg(src, cors = false) {
  return new Promise((resolve) => {
    if (!src) return resolve(null);
    const img = new Image();
    if (cors) img.crossOrigin = "anonymous";
    img.onload = () => resolve(img); img.onerror = () => resolve(null);
    img.src = src;
  });
}

// Foto anggota bisa berupa data URL atau /api/files/... (butuh login) -> diambil lewat api agar token ikut.
async function loadPhoto(photo) {
  if (!photo) return null;
  try {
    if (photo.startsWith("data:")) return await loadImg(photo);
    if (photo.startsWith("/api/")) {
      const res = await api.get(photo.slice(4), { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const img = await loadImg(url);
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      return img;
    }
    return await loadImg(photo, true);
  } catch { return null; }
}

async function ensureFonts() {
  if (!document.fonts || !document.fonts.load) return;
  const specs = [`900 40px "Exo 2"`, `800 40px "Exo 2"`, `700 40px "Exo 2"`, `800 20px "Plus Jakarta Sans"`, `700 20px "Plus Jakarta Sans"`, `600 20px "Plus Jakarta Sans"`];
  await Promise.race([Promise.all(specs.map((s) => document.fonts.load(s).catch(() => null))), new Promise((r) => setTimeout(r, 2500))]);
}

// ===== Helper gambar =====
const font = (ctx, size, weight = 700, family = BODY) => { ctx.font = `${weight} ${size}px ${family}`; };
function fitFont(ctx, text, maxW, size, weight, family, min = 10) {
  let s = size; font(ctx, s, weight, family);
  while (s > min && ctx.measureText(text).width > maxW) { s -= 0.5; font(ctx, s, weight, family); }
  return s;
}
function ellipsis(ctx, text, maxW) {
  if (ctx.measureText(text).width <= maxW) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(`${t}…`).width > maxW) t = t.slice(0, -1);
  return `${t.trimEnd()}…`;
}
// Nama juara: satu baris bila muat; kalau tidak, dibagi dua baris seimbang (tidak dikecilkan berlebihan).
function nameLines(ctx, text, maxW, size) {
  const one = fitFont(ctx, text, maxW, size, 900, HEAD, size - 4);
  if (ctx.measureText(text).width <= maxW) return { size: one, rows: [text] };
  const words = text.split(/\s+/).filter(Boolean);
  const s2 = size - 3; font(ctx, s2, 900, HEAD);
  if (words.length < 2) return { size: s2, rows: [ellipsis(ctx, text, maxW)] };
  let best = null;
  for (let k = 1; k < words.length; k += 1) {
    const a = words.slice(0, k).join(" "), b = words.slice(k).join(" ");
    const score = Math.max(ctx.measureText(a).width, ctx.measureText(b).width);
    if (!best || score < best.score) best = { a, b, score };
  }
  return { size: s2, rows: [ellipsis(ctx, best.a, maxW), ellipsis(ctx, best.b, maxW)] };
}
function tracked(ctx, text, x, y, spacing, align = "center") {
  const chars = [...text]; const widths = chars.map((ch) => ctx.measureText(ch).width);
  const total = widths.reduce((a, b) => a + b, 0) + spacing * (chars.length - 1);
  let cx = align === "center" ? x - total / 2 : align === "right" ? x - total : x;
  const prev = ctx.textAlign; ctx.textAlign = "left";
  chars.forEach((ch, i) => { ctx.fillText(ch, cx, y); cx += widths[i] + spacing; });
  ctx.textAlign = prev; return total;
}
function rr(ctx, x, y, w, h, r) {
  const k = Math.min(r, w / 2, h / 2);
  ctx.beginPath(); ctx.moveTo(x + k, y); ctx.arcTo(x + w, y, x + w, y + h, k); ctx.arcTo(x + w, y + h, x, y + h, k);
  ctx.arcTo(x, y + h, x, y, k); ctx.arcTo(x, y, x + w, y, k); ctx.closePath();
}
const goldGrad = (ctx, x0, y0, x1, y1) => { const g = ctx.createLinearGradient(x0, y0, x1, y1); g.addColorStop(0, C.goldD); g.addColorStop(0.28, C.goldL); g.addColorStop(0.55, C.gold); g.addColorStop(0.8, C.goldL); g.addColorStop(1, C.goldD); return g; };
function coverImage(ctx, img, x, y, w, h) {
  const r = Math.max(w / img.width, h / img.height); const iw = img.width * r, ih = img.height * r;
  ctx.drawImage(img, x + (w - iw) / 2, y + (h - ih) / 2, iw, ih);
}
function sparkle(ctx, x, y, r, alpha) {
  ctx.save(); ctx.globalAlpha = alpha; ctx.fillStyle = C.goldL; ctx.beginPath();
  ctx.moveTo(x, y - r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.quadraticCurveTo(x, y, x, y + r); ctx.quadraticCurveTo(x, y, x - r, y); ctx.quadraticCurveTo(x, y, x, y - r);
  ctx.fill(); ctx.restore();
}
function diamond(ctx, x, y, r, fill) { ctx.save(); ctx.fillStyle = fill; ctx.beginPath(); ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath(); ctx.fill(); ctx.restore(); }

function drawLogo(ctx, img, cx, cy, r) {
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,.45)"; ctx.shadowBlur = 14; ctx.shadowOffsetY = 4;
  ctx.beginPath(); ctx.arc(cx, cy, r + 5, 0, Math.PI * 2); ctx.fillStyle = goldGrad(ctx, cx - r, cy - r, cx + r, cy + r); ctx.fill();
  ctx.shadowColor = "transparent";
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill(); ctx.clip();
  if (img) { const s = Math.min((r * 1.72) / img.width, (r * 1.72) / img.height); ctx.drawImage(img, cx - (img.width * s) / 2, cy - (img.height * s) / 2, img.width * s, img.height * s); }
  ctx.restore();
}

function drawBackground(ctx, bg, L) {
  const H = L.H;
  const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, C.navy); g.addColorStop(0.5, "#0a1a40"); g.addColorStop(1, C.deep);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  if (bg) {
    ctx.save(); ctx.globalAlpha = 0.42; coverImage(ctx, bg, 0, 0, W, H * 0.54); ctx.restore();
    ctx.save(); ctx.globalAlpha = 0.18; ctx.translate(0, H); ctx.scale(1, -1); coverImage(ctx, bg, 0, 0, W, H * 0.44); ctx.restore();
  }
  const o = ctx.createLinearGradient(0, 0, 0, H);
  o.addColorStop(0, "rgba(6,16,44,.78)"); o.addColorStop(0.3, "rgba(9,25,64,.62)"); o.addColorStop(0.55, "rgba(7,18,48,.86)"); o.addColorStop(1, "rgba(4,11,32,.94)");
  ctx.fillStyle = o; ctx.fillRect(0, 0, W, H);
  // cahaya emas di belakang juara 1
  const gy = L.pb - 240;
  const glow = ctx.createRadialGradient(500, gy, 10, 500, gy, 440); glow.addColorStop(0, "rgba(247,220,132,.30)"); glow.addColorStop(0.45, "rgba(212,165,55,.10)"); glow.addColorStop(1, "rgba(212,165,55,0)");
  ctx.fillStyle = glow; ctx.fillRect(0, gy - 360, W, 720);
  ctx.save(); ctx.translate(500, gy); ctx.fillStyle = "rgba(247,220,132,.05)";
  for (let i = 0; i < 18; i += 1) { ctx.rotate((Math.PI * 2) / 18); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(-26, -540); ctx.lineTo(26, -540); ctx.closePath(); ctx.fill(); }
  ctx.restore();
  const k = H / 1414;
  [[90, 250, 7, .55], [915, 300, 9, .6], [150, 470, 5, .45], [860, 520, 6, .5], [70, 720, 5, .35], [935, 760, 7, .45], [320, 430, 4, .5], [690, 445, 5, .5]].forEach(([x, y, r, a]) => sparkle(ctx, x, y * k, r, a));
}

function drawFrame(ctx, L) {
  const bottom = L.bY - 8;
  ctx.save();
  ctx.strokeStyle = goldGrad(ctx, 0, 0, W, L.H); ctx.lineWidth = 2.6; ctx.strokeRect(14, 14, W - 28, bottom - 14);
  ctx.globalAlpha = 0.45; ctx.lineWidth = 0.8; ctx.strokeRect(22, 22, W - 44, bottom - 30);
  ctx.restore();
  [[14, 14], [W - 14, 14]].forEach(([x, y]) => diamond(ctx, x, y, 7, C.goldL));
}

function drawHeader(ctx, d, L) {
  const y = L.hy;
  drawLogo(ctx, d.schoolLogo, 102, y, L.logoR);
  drawLogo(ctx, d.libraryLogo, W - 102, y, L.logoR);
  ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
  ctx.fillStyle = C.goldL; font(ctx, 19, 800, BODY); tracked(ctx, LIBRARY_LABEL, 500, y - 24, 6);
  ctx.fillStyle = C.white; ctx.shadowColor = "rgba(0,0,0,.4)"; ctx.shadowBlur = 8;
  fitFont(ctx, d.schoolName, 600, 40, 900, HEAD); ctx.fillText(d.schoolName, 500, y + 21); ctx.shadowBlur = 0;
  ctx.fillStyle = C.soft; fitFont(ctx, d.address, 580, 16, 600, BODY); ctx.fillText(d.address, 500, y + 50);
  const dy = y + 81;
  const lg = ctx.createLinearGradient(110, 0, 890, 0); lg.addColorStop(0, "rgba(212,165,55,0)"); lg.addColorStop(0.5, C.goldL); lg.addColorStop(1, "rgba(212,165,55,0)");
  ctx.fillStyle = lg; ctx.fillRect(110, dy - 1, 780, 1.6);
  diamond(ctx, 500, dy, 7, C.gold); diamond(ctx, 476, dy, 3.5, C.goldL); diamond(ctx, 524, dy, 3.5, C.goldL);
}

function drawTitle(ctx, d, L) {
  const y = L.ty;
  ctx.textAlign = "center";
  ctx.fillStyle = C.goldL; font(ctx, 16, 800, BODY); tracked(ctx, d.eyebrow, 500, y, 4.5);
  ctx.save(); ctx.shadowColor = "rgba(0,0,0,.55)"; ctx.shadowBlur = 16; ctx.shadowOffsetY = 5;
  ctx.fillStyle = C.white; fitFont(ctx, "PERINGKAT RAJIN", 820, L.t1, 900, HEAD); ctx.fillText("PERINGKAT RAJIN", 500, y + 68);
  fitFont(ctx, d.K.title2, 880, L.t2, 900, HEAD); ctx.fillStyle = goldGrad(ctx, 160, y + 76, 840, y + 158); ctx.fillText(d.K.title2, 500, y + 68 + L.t2 * 0.87);
  ctx.restore();
  const text = `PERIODE  ·  ${d.period.toUpperCase()}`; font(ctx, 21, 800, BODY);
  const tw = [...text].reduce((a, ch) => a + ctx.measureText(ch).width, 0) + 2.6 * (text.length - 1);
  const pw = tw + 84, px = 500 - pw / 2, py = y + 68 + L.t2 * 0.87 + 20;
  ctx.save(); ctx.shadowColor = "rgba(0,0,0,.4)"; ctx.shadowBlur = 10;
  rr(ctx, px, py, pw, 42, 21); ctx.fillStyle = goldGrad(ctx, px, py, px + pw, py + 42); ctx.fill(); ctx.restore();
  rr(ctx, px + 4, py + 4, pw - 8, 34, 17); ctx.fillStyle = C.navy; ctx.fill();
  ctx.fillStyle = C.goldL; tracked(ctx, text, 500, py + 28, 2.6);
}

function drawCrown(ctx, cx, top) {
  ctx.save(); ctx.shadowColor = "rgba(0,0,0,.45)"; ctx.shadowBlur = 8;
  ctx.fillStyle = goldGrad(ctx, cx - 34, top, cx + 34, top + 40);
  ctx.beginPath(); ctx.moveTo(cx - 34, top + 38); ctx.lineTo(cx - 38, top + 6); ctx.lineTo(cx - 17, top + 22); ctx.lineTo(cx, top); ctx.lineTo(cx + 17, top + 22); ctx.lineTo(cx + 38, top + 6); ctx.lineTo(cx + 34, top + 38); ctx.closePath(); ctx.fill();
  ctx.shadowBlur = 0; ctx.fillStyle = C.navy; ctx.fillRect(cx - 34, top + 30, 68, 3);
  [[cx - 38, top + 6], [cx, top], [cx + 38, top + 6]].forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 4.5, 0, Math.PI * 2); ctx.fillStyle = C.goldL; ctx.fill(); });
  ctx.restore();
}

function drawAvatar(ctx, s, img, cx, cy, r, m) {
  ctx.save(); ctx.shadowColor = "rgba(0,0,0,.5)"; ctx.shadowBlur = 18; ctx.shadowOffsetY = 6;
  const ring = ctx.createLinearGradient(cx - r, cy - r, cx + r, cy + r); ring.addColorStop(0, m.a); ring.addColorStop(0.5, m.b); ring.addColorStop(1, m.c);
  ctx.beginPath(); ctx.arc(cx, cy, r + 7, 0, Math.PI * 2); ctx.fillStyle = ring; ctx.fill(); ctx.restore();
  ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
  if (img) coverImage(ctx, img, cx - r, cy - r, r * 2, r * 2);
  else {
    const g = ctx.createLinearGradient(cx, cy - r, cx, cy + r); g.addColorStop(0, C.mid); g.addColorStop(1, C.navy);
    ctx.fillStyle = g; ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
    ctx.fillStyle = s ? m.a : "rgba(255,255,255,.35)"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; font(ctx, r * 0.78, 900, HEAD);
    ctx.fillText(s ? initials(s.name) : "?", cx, cy + 2); ctx.textBaseline = "alphabetic";
  }
  ctx.restore();
}

function drawMedal(ctx, cx, cy, r, m, rank) {
  ctx.save(); ctx.shadowColor = "rgba(0,0,0,.5)"; ctx.shadowBlur = 8; ctx.shadowOffsetY = 3;
  const g = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.4, 1, cx, cy, r * 1.1); g.addColorStop(0, m.a); g.addColorStop(0.55, m.b); g.addColorStop(1, m.c);
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fillStyle = g; ctx.fill(); ctx.restore();
  ctx.beginPath(); ctx.arc(cx, cy, r * 0.76, 0, Math.PI * 2); ctx.lineWidth = 1.6; ctx.strokeStyle = "rgba(255,255,255,.75)"; ctx.stroke();
  ctx.fillStyle = C.navy; ctx.textAlign = "center"; ctx.textBaseline = "middle"; font(ctx, r * 1.05, 900, HEAD); ctx.fillText(String(rank), cx, cy + 1.5); ctx.textBaseline = "alphabetic";
}

function drawPedestal(ctx, cx, top, base, w, rank, m) {
  const x = cx - w / 2, depth = 16;
  ctx.save(); ctx.shadowColor = "rgba(0,0,0,.55)"; ctx.shadowBlur = 20; ctx.shadowOffsetY = 8;
  const face = ctx.createLinearGradient(0, top, 0, base); face.addColorStop(0, "#1d3f86"); face.addColorStop(1, "#0a1c45");
  ctx.fillStyle = face; ctx.fillRect(x, top + depth, w, base - top - depth); ctx.restore();
  ctx.beginPath(); ctx.moveTo(x, top + depth); ctx.lineTo(x + 14, top); ctx.lineTo(x + w - 14, top); ctx.lineTo(x + w, top + depth); ctx.closePath();
  ctx.fillStyle = goldGrad(ctx, x, top, x + w, top + depth); ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,.08)"; ctx.fillRect(x, top + depth, w * 0.5, base - top - depth);
  ctx.fillStyle = C.gold; ctx.fillRect(x, top + depth, w, 2);
  const faceH = base - top - depth;
  const label = `JUARA ${rank} · ${m.label}`;
  const showLabel = faceH >= 56;
  // Angka ditaruh di tengah area di atas label (tidak berdempetan dengan tulisan "JUARA ...")
  const areaTop = top + depth + 7, areaBottom = showLabel ? base - 26 : base - 7;
  const numSize = Math.min(72, (areaBottom - areaTop) / 0.74);
  const numY = (areaTop + areaBottom) / 2 + numSize * 0.36;
  // Angka juara: gradasi terang + bayangan & garis tepi gelap agar tetap jelas di alas biru (terutama perunggu)
  ctx.save(); ctx.textAlign = "center"; font(ctx, numSize, 900, HEAD);
  const ng = ctx.createLinearGradient(0, numY - numSize * 0.75, 0, numY); ng.addColorStop(0, "#ffffff"); ng.addColorStop(0.35, m.a); ng.addColorStop(1, m.b);
  ctx.shadowColor = "rgba(0,0,0,.6)"; ctx.shadowBlur = 8; ctx.shadowOffsetY = 3;
  ctx.lineWidth = 3; ctx.strokeStyle = "rgba(5,15,41,.85)"; ctx.lineJoin = "round"; ctx.strokeText(String(rank), cx, numY);
  ctx.shadowColor = "transparent"; ctx.fillStyle = ng; ctx.fillText(String(rank), cx, numY);
  ctx.restore();
  if (showLabel) { font(ctx, 12, 800, BODY); ctx.fillStyle = m.a; ctx.textAlign = "center"; tracked(ctx, label, cx, base - 10, 2); }
}

function drawIconGlyph(ctx, kind, cx, cy, color, s = 1) {
  ctx.save(); ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 1.8 * s; ctx.lineCap = "round"; ctx.lineJoin = "round";
  if (kind === "clock") {
    ctx.beginPath(); ctx.arc(cx, cy, 7 * s, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy - 4 * s); ctx.lineTo(cx, cy); ctx.lineTo(cx + 3.5 * s, cy + 2.2 * s); ctx.stroke();
  } else { // buku terbuka
    ctx.beginPath(); ctx.moveTo(cx, cy - 4 * s); ctx.quadraticCurveTo(cx - 4 * s, cy - 7 * s, cx - 9 * s, cy - 6 * s); ctx.lineTo(cx - 9 * s, cy + 6 * s); ctx.quadraticCurveTo(cx - 4 * s, cy + 5 * s, cx, cy + 8 * s); ctx.closePath(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy - 4 * s); ctx.quadraticCurveTo(cx + 4 * s, cy - 7 * s, cx + 9 * s, cy - 6 * s); ctx.lineTo(cx + 9 * s, cy + 6 * s); ctx.quadraticCurveTo(cx + 4 * s, cy + 5 * s, cx, cy + 8 * s); ctx.closePath(); ctx.stroke();
  }
  ctx.restore();
}

// Kolom podium: avatar + medali, lalu kartu info yang rapi (nama · kelas · nilai) di atas alas juara.
function drawPodium(ctx, d, L) {
  const base = L.pb, w = L.colW - 8;
  const spots = [{ i: 0, cx: 500 }, { i: 1, cx: 500 - L.colW - 12 }, { i: 2, cx: 500 + L.colW + 12 }];
  spots.forEach(({ i, cx }) => {
    const s = d.students[i]; const m = MEDALS[i]; const h = L.ph[i]; const r = L.ar[i]; const pt = base - h;
    drawPedestal(ctx, cx, pt, base, w, i + 1, m);
    // kartu info
    const cardW = w - 10, cardH = 130, cardY = pt - 8 - cardH, cardX = cx - cardW / 2;
    ctx.save(); ctx.shadowColor = "rgba(0,0,0,.45)"; ctx.shadowBlur = 14;
    rr(ctx, cardX, cardY, cardW, cardH, 14); ctx.fillStyle = "rgba(6,17,46,.92)"; ctx.fill(); ctx.restore();
    rr(ctx, cardX, cardY, cardW, cardH, 14); ctx.lineWidth = 1.4; ctx.strokeStyle = m.b; ctx.stroke();
    const name = s ? s.name : "Belum ada";
    const lines = nameLines(ctx, name, cardW - 24, i === 0 ? 25 : 23);
    ctx.textAlign = "center"; ctx.fillStyle = C.white; font(ctx, lines.size, 900, HEAD);
    if (lines.rows.length === 1) ctx.fillText(lines.rows[0], cx, cardY + 54);
    else { ctx.fillText(lines.rows[0], cx, cardY + 38); ctx.fillText(lines.rows[1], cx, cardY + 38 + lines.size + 1); }
    const clsY = lines.rows.length === 1 ? cardY + 78 : cardY + 83;
    ctx.fillStyle = C.soft; fitFont(ctx, s ? (s.class_name || "-") : "—", cardW - 30, 15, 600, BODY, 11);
    ctx.fillText(s ? (s.class_name || "-") : "—", cx, clsY);
    // pil nilai (waktu / buku)
    const pill = s ? d.K.pill(s) : "—";
    const pillMax = cardW - 22;
    fitFont(ctx, pill, pillMax - 46, 15, 800, BODY, 11);
    const tw = ctx.measureText(pill).width; const pw = Math.min(pillMax, tw + 46);
    const py = cardY + 95;
    rr(ctx, cx - pw / 2, py, pw, 26, 13); ctx.fillStyle = "rgba(255,255,255,.07)"; ctx.fill(); ctx.lineWidth = 1; ctx.strokeStyle = m.b; ctx.stroke();
    const startX = cx - (tw + 22) / 2;
    if (s) drawIconGlyph(ctx, d.K.icon, startX + 8, py + 13, m.a, 0.95);
    ctx.textAlign = "left"; ctx.fillStyle = m.a; ctx.fillText(pill, startX + (s ? 22 : 11), py + 18.5);
    // avatar + medali di atas kartu
    const medalR = 20, medalCy = cardY;
    const cy = medalCy - 10 - r;
    if (i === 0) drawCrown(ctx, cx, cy - r - 46);
    drawAvatar(ctx, s, d.photos[i], cx, cy, r, m);
    drawMedal(ctx, cx, medalCy, medalR, m, i + 1);
  });
}

function drawTable(ctx, d, L) {
  const x = 56, y = L.tbY, w = W - 112, rh = L.rowH, h = 90 + rh * 7;
  ctx.save(); ctx.shadowColor = "rgba(0,0,0,.5)"; ctx.shadowBlur = 18;
  rr(ctx, x, y, w, h, 16); ctx.fillStyle = "rgba(6,17,46,.9)"; ctx.fill(); ctx.restore();
  rr(ctx, x, y, w, h, 16); ctx.lineWidth = 1.2; ctx.strokeStyle = "rgba(212,165,55,.55)"; ctx.stroke();
  ctx.textAlign = "left"; ctx.fillStyle = C.goldL; font(ctx, 17, 900, HEAD); tracked(ctx, "PERINGKAT 4 – 10", x + 22, y + 30, 2.4, "left");
  ctx.textAlign = "right"; ctx.fillStyle = C.muted; font(ctx, 12, 600, BODY); ctx.fillText(d.note, x + w - 22, y + 29);
  const cols = { rank: x + 74, name: x + 140, cls: x + 590, time: x + w - 100 };
  const hy = y + 44;
  rr(ctx, x + 14, hy, w - 28, 38, 9); ctx.fillStyle = goldGrad(ctx, x, hy, x + w, hy + 38); ctx.fill();
  ctx.fillStyle = C.navy; font(ctx, 14, 900, BODY);
  ctx.textAlign = "center"; tracked(ctx, "PERINGKAT", cols.rank, hy + 25, 1.6);
  ctx.textAlign = "left"; tracked(ctx, d.guru ? "NAMA GURU" : "NAMA SISWA", cols.name, hy + 25, 1.6, "left");
  ctx.textAlign = "center"; tracked(ctx, "KELAS", cols.cls, hy + 25, 1.6); tracked(ctx, d.K.colHead, cols.time, hy + 25, 1.6);
  const rows = d.students.slice(3, 10);
  for (let k = 0; k < 7; k += 1) {
    const ry = hy + 44 + k * rh; const s = rows[k];
    rr(ctx, x + 14, ry, w - 28, rh - 4, 7); ctx.fillStyle = k % 2 ? "rgba(255,255,255,.035)" : "rgba(255,255,255,.085)"; ctx.fill();
    const mid = ry + (rh - 4) / 2;
    ctx.beginPath(); ctx.arc(cols.rank, mid, 13, 0, Math.PI * 2); ctx.fillStyle = s ? C.navy : "rgba(255,255,255,.05)"; ctx.fill();
    ctx.lineWidth = 1.4; ctx.strokeStyle = s ? C.gold : "rgba(212,165,55,.3)"; ctx.stroke();
    ctx.textAlign = "center"; ctx.fillStyle = s ? C.goldL : C.muted; font(ctx, 15, 900, HEAD); ctx.fillText(String(k + 4), cols.rank, mid + 5.5);
    ctx.textAlign = "left";
    if (s) {
      ctx.fillStyle = C.white; font(ctx, 18, 700, BODY); ctx.fillText(ellipsis(ctx, s.name, cols.cls - cols.name - 90), cols.name, mid + 6.5);
      ctx.textAlign = "center"; ctx.fillStyle = C.soft; fitFont(ctx, s.class_name || "-", 150, 16, 600, BODY); ctx.fillText(s.class_name || "-", cols.cls, mid + 6);
      ctx.fillStyle = C.goldL; fitFont(ctx, d.K.col(s), 170, 17, 800, BODY, 11); ctx.fillText(d.K.col(s), cols.time, mid + 6);
    } else {
      ctx.fillStyle = "rgba(207,217,236,.4)"; font(ctx, 16, 600, BODY); ctx.fillText("—", cols.name, mid + 6);
      ctx.textAlign = "center"; ctx.fillText("—", cols.cls, mid + 6); ctx.fillText("—", cols.time, mid + 6);
    }
  }
}

function drawStatIcon(ctx, kind, cx, cy) {
  ctx.save(); ctx.strokeStyle = C.navy; ctx.fillStyle = C.navy; ctx.lineWidth = 2.6; ctx.lineCap = "round"; ctx.lineJoin = "round";
  if (kind === "people") {
    ctx.beginPath(); ctx.arc(cx - 5, cy - 6, 6, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx - 5, cy + 13, 11, Math.PI, 0); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + 9, cy - 3, 4.5, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + 9, cy + 12, 8, Math.PI, 0); ctx.fill();
  } else if (kind === "book") {
    ctx.restore(); drawIconGlyph(ctx, "book", cx, cy - 1, C.navy, 1.45); return;
  } else if (kind === "trophy") {
    ctx.beginPath(); ctx.moveTo(cx - 10, cy - 12); ctx.lineTo(cx + 10, cy - 12); ctx.lineTo(cx + 8, cy + 1); ctx.quadraticCurveTo(cx, cy + 8, cx - 8, cy + 1); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.arc(cx - 11, cy - 6, 5, Math.PI * 0.5, Math.PI * 1.5); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx + 11, cy - 6, 5, -Math.PI * 0.5, Math.PI * 0.5); ctx.stroke();
    ctx.fillRect(cx - 2, cy + 4, 4, 7); ctx.fillRect(cx - 8, cy + 11, 16, 4);
  } else {
    ctx.beginPath(); ctx.moveTo(cx + 10, cy - 11); ctx.lineTo(cx - 10, cy + 11); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx - 7, cy - 7, 4.5, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx + 7, cy + 7, 4.5, 0, Math.PI * 2); ctx.stroke();
  }
  ctx.restore();
}

function drawStats(ctx, d, L) {
  const y = L.sY, h = L.sH, gap = 18, w = (W - 112 - gap * 2) / 3;
  d.stats.forEach((st, k) => {
    const x = 56 + k * (w + gap);
    ctx.save(); ctx.shadowColor = "rgba(0,0,0,.5)"; ctx.shadowBlur = 14;
    rr(ctx, x, y, w, h, 14); const g = ctx.createLinearGradient(x, y, x, y + h); g.addColorStop(0, "#173a7d"); g.addColorStop(1, "#0b1d45"); ctx.fillStyle = g; ctx.fill(); ctx.restore();
    rr(ctx, x, y, w, h, 14); ctx.lineWidth = 1.2; ctx.strokeStyle = "rgba(212,165,55,.6)"; ctx.stroke();
    ctx.fillStyle = goldGrad(ctx, x, y, x + w, y); ctx.fillRect(x + 18, y, w - 36, 3);
    ctx.beginPath(); ctx.arc(x + 44, y + h / 2, 25, 0, Math.PI * 2); ctx.fillStyle = goldGrad(ctx, x + 19, y, x + 69, y + h); ctx.fill();
    drawStatIcon(ctx, st.icon, x + 44, y + h / 2);
    const mid = y + h / 2;
    ctx.textAlign = "left"; ctx.fillStyle = C.goldL; fitFont(ctx, st.label, w - 100 - 1.2 * st.label.length, 12, 800, BODY, 8); tracked(ctx, st.label, x + 82, mid - 10, 1.2, "left");
    ctx.fillStyle = C.white; fitFont(ctx, st.value, w - 96, 32, 900, HEAD, 16); ctx.fillText(st.value, x + 82, mid + 25);
  });
}

function drawBook(ctx, cx, cy) {
  ctx.save(); ctx.fillStyle = C.navy;
  ctx.beginPath(); ctx.moveTo(cx, cy - 8); ctx.quadraticCurveTo(cx - 12, cy - 14, cx - 24, cy - 11); ctx.lineTo(cx - 24, cy + 12); ctx.quadraticCurveTo(cx - 12, cy + 9, cx, cy + 15); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.moveTo(cx, cy - 8); ctx.quadraticCurveTo(cx + 12, cy - 14, cx + 24, cy - 11); ctx.lineTo(cx + 24, cy + 12); ctx.quadraticCurveTo(cx + 12, cy + 9, cx, cy + 15); ctx.closePath(); ctx.fill();
  ctx.restore();
}
function drawBanner(ctx, L) {
  const y = L.bY, h = L.H - y;
  ctx.fillStyle = goldGrad(ctx, 0, y, W, y + h); ctx.fillRect(0, y, W, h);
  ctx.fillStyle = "rgba(255,255,255,.35)"; ctx.fillRect(0, y, W, 1.5);
  ctx.fillStyle = C.navy; ctx.fillRect(0, y + 6, W, 1.2); ctx.fillRect(0, y + h - 7, W, 1.2);
  const cy = y + h / 2;
  ctx.textAlign = "center"; ctx.fillStyle = C.navy; fitFont(ctx, POSTER_SLOGAN, 760, 29, 900, HEAD); tracked(ctx, POSTER_SLOGAN, 500, cy + 10, 2.2);
  drawBook(ctx, 70, cy); drawBook(ctx, W - 70, cy);
}

/** Susun data poster dari respons peringkat yang sedang tampil + pengaturan sekolah. */
export function posterData(lb, settings = {}, audience = "siswa", kind = "kunjungan") {
  const guru = audience === "guru";
  const K = KINDS[kind] || KINDS.kunjungan;
  const students = (lb.students || []).slice(0, 10);
  const top = (lb.classes || [])[0];
  const stats = guru
    ? [
      { icon: "people", label: K.statTotal, value: num(lb[K.total]) },
      { icon: "trophy", label: kind === "pinjam" ? "GURU AKTIF MEMINJAM" : "GURU AKTIF BERKUNJUNG", value: `${lb.active_students || 0} guru` },
      { icon: K.icon === "book" ? "book" : "percent", ...K.guruSum(students) },
    ]
    : [
      { icon: kind === "pinjam" ? "book" : "people", label: K.statTotal, value: num(lb[K.total]) },
      { icon: "trophy", label: K.statClass, value: top ? top.class_name : "-" },
      { icon: "percent", label: K.statPct, value: top ? pctText(top.pct) : "0%" },
    ];
  const today = new Date().toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
  return {
    guru, kind, K, students, stats,
    period: lb.label || lb.month || "",
    eyebrow: guru ? "LAPORAN BULANAN · GURU" : "LAPORAN BULANAN · SISWA",
    schoolName: (settings.card_school_name || "SMA NEGERI 1 ABUNG TENGAH").toUpperCase(),
    address: settings.card_address || "Jln Raya Subik, Desa Pekurun Selatan",
    note: `Sumber: Laporan Peringkat Perpustakaan · ${today}`,
    schoolLogoSrc: settings.school_logo || SCHOOL_LOGO,
    libraryLogoSrc: settings.library_logo || LIBRARY_LOGO,
  };
}

/** Gambar poster ke canvas (ukuran penuh) dan kembalikan canvas-nya. */
export async function renderPoster(lb, settings, { audience = "siswa", kind = "kunjungan", format = "a4" } = {}) {
  const L = POSTER_FORMATS[format] || POSTER_FORMATS.a4;
  const d = posterData(lb, settings, audience, kind);
  const [bg, schoolLogo, libraryLogo, ...photos] = await Promise.all([
    loadImg(BG_URL), loadImg(d.schoolLogoSrc), loadImg(d.libraryLogoSrc), ...d.students.slice(0, 3).map((s) => loadPhoto(s.photo)),
    ensureFonts(),
  ]);
  Object.assign(d, { schoolLogo, libraryLogo, photos });
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(W * L.scale); canvas.height = Math.round(L.H * L.scale);
  const ctx = canvas.getContext("2d");
  ctx.scale(L.scale, L.scale); ctx.imageSmoothingQuality = "high";
  drawBackground(ctx, bg, L); drawFrame(ctx, L); drawHeader(ctx, d, L); drawTitle(ctx, d, L);
  drawPodium(ctx, d, L); drawTable(ctx, d, L); drawStats(ctx, d, L); drawBanner(ctx, L);
  return canvas;
}

/** Buat poster PNG lalu unduh. format: "a4" | "story" ; kind: "kunjungan" | "pinjam". */
export async function downloadPoster(lb, settings, { audience = "siswa", kind = "kunjungan", format = "a4" } = {}) {
  const L = POSTER_FORMATS[format] || POSTER_FORMATS.a4;
  const K = KINDS[kind] || KINDS.kunjungan;
  const canvas = await renderPoster(lb, settings, { audience, kind, format });
  const blob = await new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Gagal membuat PNG"))), "image/png"));
  const png = new Blob([withPngDpi(await blob.arrayBuffer(), L.dpi)], { type: "image/png" });
  saveBlob(png, `poster-peringkat-${K.file}-${lb.month || "periode"}${audience === "guru" ? "-guru" : ""}-${L.suffix}.png`);
  return png;
}
