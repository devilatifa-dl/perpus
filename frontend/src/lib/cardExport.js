// Ekspor kartu anggota ke PNG resolusi tinggi (300 / 600 DPI) untuk dicetak.
// - Kartu dirender ulang dari tampilan aslinya (teks & QR vektor) pada skala piksel tinggi,
//   sehingga teks tidak blur dan foto memakai resolusi aslinya (tidak diperbesar dari layar).
// - PNG diberi metadata DPI (chunk pHYs) agar aplikasi cetak/percetakan membaca ukuran fisik 86 x 56 mm.
import { toCanvas, getFontEmbedCSS } from "html-to-image";

export const CARD_MM = { w: 86, h: 56 };
export const DPI_OPTIONS = [300, 600];
export const DEFAULT_DPI = 600;

// Ukuran desain kartu (px CSS) yang dipakai juga di cetak massal (lihat Extras.css .print-slot)
const DESIGN = { landscape: { w: 470, h: 306 }, portrait: { w: 320, h: 491 } };

export const pxForDpi = (mm, dpi) => Math.round((mm / 25.4) * dpi);
export const cardPixelSize = (dpi, portrait = false) => {
  const w = pxForDpi(portrait ? CARD_MM.h : CARD_MM.w, dpi); const h = pxForDpi(portrait ? CARD_MM.w : CARD_MM.h, dpi);
  return { w, h };
};

// ===== CRC32 + chunk pHYs (DPI) =====
let CRC_TABLE = null;
function crc32(bytes) {
  if (!CRC_TABLE) {
    CRC_TABLE = new Uint32Array(256);
    for (let n = 0; n < 256; n += 1) { let c = n; for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; CRC_TABLE[n] = c >>> 0; }
  }
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/** Sisipkan chunk pHYs (piksel per meter) setelah IHDR. */
export function withPngDpi(buffer, dpi) {
  const src = new Uint8Array(buffer);
  const ppm = Math.round(dpi / 0.0254);
  const chunk = new Uint8Array(21); const dv = new DataView(chunk.buffer);
  dv.setUint32(0, 9); chunk.set([0x70, 0x48, 0x59, 0x73], 4); // "pHYs"
  dv.setUint32(8, ppm); dv.setUint32(12, ppm); chunk[16] = 1; // satuan: meter
  dv.setUint32(17, crc32(chunk.subarray(4, 17)));
  const ihdrEnd = 8 + 25; // signature + IHDR
  const out = new Uint8Array(src.length + chunk.length);
  out.set(src.subarray(0, ihdrEnd), 0); out.set(chunk, ihdrEnd); out.set(src.subarray(ihdrEnd), ihdrEnd + chunk.length);
  return out;
}

const canvasToBlob = (canvas) => new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Gagal membuat PNG"))), "image/png"));

const waitImages = (root) => Promise.all([...root.querySelectorAll("img")].map((img) => (img.complete && img.naturalWidth ? (img.decode ? img.decode().catch(() => {}) : null) : new Promise((r) => { img.onload = r; img.onerror = r; }))));

// ===== Sematkan font kartu (lokal /fonts + Google Fonts) ke PNG =====
const fontFileCache = new Map();
const toDataUrl = async (url) => {
  if (fontFileCache.has(url)) return fontFileCache.get(url);
  const p = fetch(url).then((r) => { if (!r.ok) throw new Error("font"); return r.blob(); })
    .then((b) => new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(b); }));
  fontFileCache.set(url, p); return p;
};
async function collectFontFaces() {
  const blocks = [];
  for (const sheet of [...document.styleSheets]) {
    let text = "";
    try { text = [...sheet.cssRules].filter((r) => r.type === CSSRule.FONT_FACE_RULE).map((r) => r.cssText).join("\n"); }
    catch (e) { if (sheet.href) { try { text = await (await fetch(sheet.href)).text(); } catch (err) { text = ""; } } }
    const base = sheet.href || document.baseURI;
    for (const m of text.matchAll(/@font-face\s*{[^}]*}/g)) blocks.push({ css: m[0], base });
  }
  return blocks;
}
const familyOf = (css) => ((css.match(/font-family:\s*["']?([^;"']+)["']?/i) || [])[1] || "").trim().toLowerCase();
const usedFamilies = (root) => {
  const set = new Set();
  [root, ...root.querySelectorAll("*")].forEach((el) => getComputedStyle(el).fontFamily.split(",").forEach((f) => set.add(f.trim().replace(/^["']|["']$/g, "").toLowerCase())));
  return set;
};
async function buildFontCss(root) {
  const used = usedFamilies(root);
  const faces = (await collectFontFaces()).filter((b) => used.has(familyOf(b.css)));
  // Google Fonts memecah per subset unicode; latin cukup untuk kartu (hemat ukuran)
  const pick = faces.filter((b) => !/unicode-range/i.test(b.css) || /U\+0000-00FF/i.test(b.css));
  const out = await Promise.all(pick.map(async (b) => {
    let css = b.css; const urls = [...css.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/g)].map((m) => m[1]);
    for (const u of urls) {
      if (u.startsWith("data:")) continue;
      try { css = css.split(u).join(await toDataUrl(new URL(u, b.base).href)); } catch (e) { /* lewati font yang gagal diambil */ }
    }
    return css;
  }));
  return out.join("\n");
}

let fontCssCache = null;

/**
 * Render satu elemen kartu (depan .id-card atau belakang .id-card-back) menjadi PNG ber-DPI.
 * @param {HTMLElement} cardEl elemen kartu yang sedang tampil di halaman
 * @param {{dpi?:number, hideFields?:boolean}} opts
 * @returns {Promise<{blob:Blob, width:number, height:number, dpi:number}>}
 */
export async function renderCardPng(cardEl, { dpi = DEFAULT_DPI, hideFields = true } = {}) {
  if (!cardEl) throw new Error("Kartu tidak ditemukan");
  const portrait = cardEl.classList.contains("layout-portrait");
  const d = portrait ? DESIGN.portrait : DESIGN.landscape;
  const target = cardPixelSize(dpi, portrait);
  // Wadah di luar layar dengan ukuran desain tetap (sama seperti slot cetak massal, tanpa zoom)
  const host = document.createElement("div"); host.className = "card-export-host"; host.setAttribute("aria-hidden", "true");
  const slot = document.createElement("div"); slot.className = `print-slot card-export-slot${portrait ? " portrait" : ""}`;
  const clone = cardEl.cloneNode(true);
  clone.removeAttribute("id"); clone.style.width = `${d.w}px`; clone.style.height = `${d.h}px`;
  // Sama dengan hasil cetak: baris Kelas & Mapel tidak ikut
  if (hideFields) clone.querySelectorAll('[data-testid="card-class"],[data-testid="card-subject"]').forEach((n) => n.remove());
  slot.appendChild(clone); host.appendChild(slot); document.body.appendChild(host);
  try {
    if (document.fonts?.ready) await document.fonts.ready;
    await waitImages(clone);
    const famKey = [...usedFamilies(clone)].sort().join("|");
    if (!fontCssCache || fontCssCache.key !== famKey) {
      let css = "";
      try { css = await buildFontCss(clone); } catch (e) { css = ""; }
      if (!css) { try { css = await getFontEmbedCSS(clone); } catch (e) { css = ""; } }
      fontCssCache = { key: famKey, css };
    }
    const canvas = await toCanvas(clone, {
      // html-to-image: ukuran kanvas akhir = canvasWidth × pixelRatio → 86 mm pada DPI terpilih
      width: d.w, height: d.h, canvasWidth: d.w, canvasHeight: d.h, pixelRatio: target.w / d.w,
      cacheBust: false, fontEmbedCSS: fontCssCache.css || undefined, skipAutoScale: true,
      style: { margin: "0", zoom: "1", boxShadow: "none", transform: "none" },
    });
    const png = await canvasToBlob(canvas);
    const bytes = withPngDpi(await png.arrayBuffer(), dpi);
    return { blob: new Blob([bytes], { type: "image/png" }), width: canvas.width, height: canvas.height, dpi };
  } finally {
    host.remove();
  }
}

export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

export const safeName = (s) => String(s || "kartu").normalize("NFKD").replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "-").slice(0, 60) || "kartu";

/** Satu kartu → unduh PNG. */
export async function downloadCardPng(cardEl, member, dpi = DEFAULT_DPI) {
  const r = await renderCardPng(cardEl, { dpi });
  saveBlob(r.blob, `kartu-${member?.id || "anggota"}-${safeName(member?.name)}-${dpi}dpi.png`);
  return r;
}

/** Banyak kartu → satu ZIP berisi PNG ber-DPI. `items` = [{el, name}] */
export async function downloadCardsZip(items, zipName, dpi = DEFAULT_DPI, onProgress) {
  const { default: JSZip } = await import("jszip");
  const zip = new JSZip();
  for (let i = 0; i < items.length; i += 1) {
    onProgress?.(i + 1, items.length);
    const r = await renderCardPng(items[i].el, { dpi });
    zip.file(items[i].name, r.blob);
  }
  zip.file("BACA-SAYA.txt", `Kartu anggota PNG ${dpi} DPI\r\nUkuran fisik tiap kartu: 86 x 56 mm (lanskap) atau 56 x 86 mm (potret).\r\nSaat mencetak pilih skala 100% / ukuran sebenarnya agar ukuran kartu tepat.\r\n`);
  const blob = await zip.generateAsync({ type: "blob", compression: "STORE" });
  saveBlob(blob, zipName);
  return blob;
}
