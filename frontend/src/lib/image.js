// Pengecil gambar otomatis di browser (tanpa mengurangi kualitas tampilan).
// - Ukuran sisi terpanjang dibatasi sesuai kegunaan (foto kartu, sampul, logo).
// - Diperkecil bertahap dengan penghalusan "high" agar tetap tajam.
// - JPEG kualitas tinggi (0.92); logo transparan tetap PNG.
// - Gambar yang sudah kecil tidak diubah sama sekali.

export const IMAGE_PRESETS = {
  photo: { maxSide: 900, targetKB: 350, label: "Foto" },
  cover: { maxSide: 1000, targetKB: 400, label: "Sampul" },
  logo: { maxSide: 600, targetKB: 300, label: "Logo" },
};

const MAX_INPUT_MB = 25;
const QUALITY_STEPS = [0.92, 0.9, 0.87, 0.84];

export const fmtSize = (bytes) => bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
const dataUrlBytes = (u) => Math.round(((u.length - u.indexOf(",") - 1) * 3) / 4);

const readAsDataUrl = (file) => new Promise((resolve, reject) => {
  const r = new FileReader(); r.onload = () => resolve(r.result); r.onerror = () => reject(new Error("Berkas tidak dapat dibaca")); r.readAsDataURL(file);
});

const loadImage = (file) => new Promise((resolve, reject) => {
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.decoding = "async";
  img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
  img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Format gambar tidak didukung. Gunakan JPG, PNG, atau WEBP.")); };
  img.src = url; // browser modern otomatis memutar sesuai EXIF foto HP
});

function hasTransparency(img) {
  const s = 64; const c = document.createElement("canvas"); c.width = s; c.height = s;
  const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(img, 0, 0, s, s);
  const d = x.getImageData(0, 0, s, s).data;
  for (let i = 3; i < d.length; i += 4) if (d[i] < 250) return true;
  return false;
}

// Perkecil bertahap (setengah demi setengah) supaya hasil tetap halus & tajam
function drawScaled(img, w, h, opaque) {
  let src = img; let sw = img.naturalWidth || img.width; let sh = img.naturalHeight || img.height;
  while (sw / 2 >= w * 1.0001 && sh / 2 >= h * 1.0001) {
    const c = document.createElement("canvas"); c.width = Math.round(sw / 2); c.height = Math.round(sh / 2);
    const x = c.getContext("2d"); x.imageSmoothingEnabled = true; x.imageSmoothingQuality = "high";
    x.drawImage(src, 0, 0, c.width, c.height);
    src = c; sw = c.width; sh = c.height;
  }
  const out = document.createElement("canvas"); out.width = w; out.height = h;
  const ox = out.getContext("2d"); ox.imageSmoothingEnabled = true; ox.imageSmoothingQuality = "high";
  if (opaque) { ox.fillStyle = "#ffffff"; ox.fillRect(0, 0, w, h); }
  ox.drawImage(src, 0, 0, w, h);
  return out;
}

/**
 * @returns {Promise<{dataUrl:string, info:{changed:boolean, before:number, after:number, width:number, height:number}}>}
 */
export async function optimizeImage(file, kind = "photo") {
  if (!file) return { dataUrl: "", info: null };
  if (!/^image\//.test(file.type) && !/\.(jpe?g|png|webp|gif|bmp|heic|heif)$/i.test(file.name || "")) throw new Error("Pilih berkas gambar (JPG, PNG, atau WEBP).");
  if (file.size > MAX_INPUT_MB * 1024 * 1024) throw new Error(`Gambar terlalu besar (maks ${MAX_INPUT_MB} MB).`);
  const p = IMAGE_PRESETS[kind] || IMAGE_PRESETS.photo;
  const img = await loadImage(file);
  const w0 = img.naturalWidth || img.width; const h0 = img.naturalHeight || img.height;
  if (!w0 || !h0) throw new Error("Gambar tidak valid.");
  const scale = Math.min(1, p.maxSide / Math.max(w0, h0));
  const smallEnough = scale === 1 && file.size <= p.targetKB * 1024 && /image\/(jpeg|png|webp)/.test(file.type);
  if (smallEnough) {
    // Sudah kecil: simpan apa adanya, kualitas 100% asli
    const dataUrl = await readAsDataUrl(file);
    return { dataUrl, info: { changed: false, before: file.size, after: file.size, width: w0, height: h0 } };
  }
  const keepPng = kind === "logo" && hasTransparency(img);
  let w = Math.max(1, Math.round(w0 * scale)); let h = Math.max(1, Math.round(h0 * scale));
  let best = null;
  for (let round = 0; round < 4; round += 1) {
    const canvas = drawScaled(img, w, h, !keepPng);
    if (keepPng) {
      best = canvas.toDataURL("image/png");
    } else {
      for (const q of QUALITY_STEPS) {
        best = canvas.toDataURL("image/jpeg", q);
        if (dataUrlBytes(best) <= p.targetKB * 1024) break;
      }
    }
    if (dataUrlBytes(best) <= p.targetKB * 1024 || Math.max(w, h) <= 480) break;
    w = Math.round(w * 0.85); h = Math.round(h * 0.85);
  }
  // Jika hasil justru lebih besar dari aslinya (jarang), pakai berkas asli bila ukurannya wajar
  if (dataUrlBytes(best) >= file.size && scale === 1 && /image\/(jpeg|png|webp)/.test(file.type)) {
    const dataUrl = await readAsDataUrl(file);
    return { dataUrl, info: { changed: false, before: file.size, after: file.size, width: w0, height: h0 } };
  }
  return { dataUrl: best, info: { changed: true, before: file.size, after: dataUrlBytes(best), width: w, height: h } };
}

// ===== Potong foto anggota =====
// Kotak foto kartu berukuran ±84×98 (rasio 6:7). Hasil potong 600×700px: tajam untuk layar & cetak.
export const CARD_PHOTO = { width: 600, height: 700, targetKB: 300 };

const loadSrc = (src) => new Promise((resolve, reject) => {
  const img = new Image();
  img.onload = () => resolve(img);
  img.onerror = () => reject(new Error("Gambar tidak dapat dibuka"));
  img.src = src;
});

/** Salinan kerja (maks 1800px) agar penggeseran lancar di HP dan memori aman saat diputar. */
export async function prepareForCrop(file) {
  if (!file) throw new Error("Pilih foto dulu");
  if (!/^image\//.test(file.type) && !/\.(jpe?g|png|webp|gif|bmp|heic|heif)$/i.test(file.name || "")) throw new Error("Pilih berkas gambar (JPG, PNG, atau WEBP).");
  if (file.size > MAX_INPUT_MB * 1024 * 1024) throw new Error(`Gambar terlalu besar (maks ${MAX_INPUT_MB} MB).`);
  const img = await loadImage(file);
  const w0 = img.naturalWidth || img.width; const h0 = img.naturalHeight || img.height;
  if (!w0 || !h0) throw new Error("Gambar tidak valid.");
  const scale = Math.min(1, 1800 / Math.max(w0, h0));
  const c = drawScaled(img, Math.round(w0 * scale), Math.round(h0 * scale), true);
  return { src: c.toDataURL("image/jpeg", 0.95), before: file.size };
}

/** Potong sesuai area dari react-easy-crop (piksel, termasuk putaran) → JPEG kualitas tinggi. */
export async function cropToDataUrl(src, area, rotation = 0) {
  const img = await loadSrc(src);
  const rad = (rotation * Math.PI) / 180;
  const iw = img.naturalWidth; const ih = img.naturalHeight;
  const bw = Math.round(Math.abs(Math.cos(rad) * iw) + Math.abs(Math.sin(rad) * ih));
  const bh = Math.round(Math.abs(Math.sin(rad) * iw) + Math.abs(Math.cos(rad) * ih));
  const rot = document.createElement("canvas"); rot.width = bw; rot.height = bh;
  const rx = rot.getContext("2d"); rx.imageSmoothingEnabled = true; rx.imageSmoothingQuality = "high";
  rx.fillStyle = "#ffffff"; rx.fillRect(0, 0, bw, bh);
  rx.translate(bw / 2, bh / 2); rx.rotate(rad); rx.drawImage(img, -iw / 2, -ih / 2);
  const cw = Math.max(1, Math.round(area.width)); const ch = Math.max(1, Math.round(area.height));
  const cut = document.createElement("canvas"); cut.width = cw; cut.height = ch;
  const cx = cut.getContext("2d"); cx.fillStyle = "#ffffff"; cx.fillRect(0, 0, cw, ch);
  cx.drawImage(rot, Math.round(area.x), Math.round(area.y), cw, ch, 0, 0, cw, ch);
  // Tidak memperbesar foto kecil (agar tidak buram); hanya diperkecil bila lebih besar dari 600×700
  const s = Math.min(1, CARD_PHOTO.width / cw);
  const ow = Math.max(1, Math.round(cw * s)); const oh = Math.max(1, Math.round(ch * s));
  const out = drawScaled(cut, ow, oh, true);
  let url = "";
  for (const q of QUALITY_STEPS) { url = out.toDataURL("image/jpeg", q); if (dataUrlBytes(url) <= CARD_PHOTO.targetKB * 1024) break; }
  return { dataUrl: url, info: { changed: true, cropped: true, after: dataUrlBytes(url), width: ow, height: oh } };
}
