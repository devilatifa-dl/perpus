import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true });
export const fmt = (value) => new Intl.NumberFormat("id-ID").format(value || 0);
export const fmtDate = (d, opts = { day: "numeric", month: "short", year: "numeric" }) => d ? new Date(d).toLocaleDateString("id-ID", opts) : "-";

export const SCHOOL_LOGO = "/logo-sekolah.png";
export const LIBRARY_LOGO = "/logo-perpustakaan.png";
export const DEFAULT_SETTINGS = { school_logo: "", library_logo: "", card_theme: "navy", card_layout: "classic", card_show_qr: true, card_show_address: true, card_title: "KARTU ANGGOTA PERPUSTAKAAN", card_school_name: "SMA NEGERI 1 ABUNG TENGAH", card_font: "modern", card_font_size: "sedang", card_school_spacing: 0, card_school_logo_pos: "kiri", card_library_logo_pos: "kanan", card_photo_pos: "kiri", card_qr_pos: "atas", card_back_title: "PERATURAN & TATA TERTIB PERPUSTAKAAN", card_back_rules: "Kartu ini wajib dibawa setiap meminjam dan mengembalikan buku.\nKembalikan buku tepat waktu sesuai tanggal yang ditentukan petugas.\nJaga buku tetap bersih; dilarang melipat, mencoret, atau merobek.\nBuku yang hilang atau rusak wajib diganti dengan judul yang sama.\nKartu tidak boleh dipinjamkan kepada orang lain.\nJika kartu ini ditemukan, mohon kembalikan ke Perpustakaan SMANSA.", card_back_web: "perpustakaan.sman1abungtengah.sch.id" };
export const CARD_THEMES = [["navy", "Biru Navy"], ["emerald", "Hijau Zamrud"], ["maroon", "Merah Maroon"], ["sunset", "Jingga Senja"], ["midnight", "Hitam Emas"], ["light", "Putih Bersih"], ["book", "Tema Buku"]];
export const CARD_LAYOUTS = [["classic", "Klasik", "Foto kiri, QR di atas"], ["modern", "Modern", "QR kiri, foto kanan"], ["portrait", "Potret", "Vertikal, QR di bawah"]];
export const CARD_FONTS = [["modern", "Modern"], ["klasik", "Klasik"], ["elegan", "Elegan"], ["mono", "Monospace"]];
export const CARD_FONT_SIZES = [["kecil", "Kecil"], ["sedang", "Sedang"], ["besar", "Besar"]];
export const CARD_POS = { logo: [["kiri", "Kiri"], ["kanan", "Kanan"]], photo: [["kiri", "Kiri"], ["kanan", "Kanan"]], qr: [["atas", "Atas"], ["bawah", "Bawah"]] };
export const CARD_PRESETS = [
  ["klasik-navy", "Klasik Navy", { card_theme: "navy", card_layout: "classic", card_font: "modern", card_font_size: "sedang", card_school_logo_pos: "kiri", card_library_logo_pos: "kiri", card_photo_pos: "kiri", card_qr_pos: "atas" }],
  ["buku-elegan", "Buku Elegan", { card_theme: "book", card_layout: "classic", card_font: "elegan", card_font_size: "besar", card_school_logo_pos: "kiri", card_library_logo_pos: "kanan", card_photo_pos: "kiri", card_qr_pos: "atas" }],
  ["modern-zamrud", "Modern Zamrud", { card_theme: "emerald", card_layout: "modern", card_font: "modern", card_font_size: "sedang", card_school_logo_pos: "kiri", card_library_logo_pos: "kanan", card_photo_pos: "kanan", card_qr_pos: "bawah" }],
  ["potret-maroon", "Potret Maroon", { card_theme: "maroon", card_layout: "portrait", card_font: "klasik", card_font_size: "sedang", card_school_logo_pos: "kiri", card_library_logo_pos: "kanan", card_photo_pos: "kiri", card_qr_pos: "bawah" }],
  ["hitam-emas", "Hitam Emas", { card_theme: "midnight", card_layout: "classic", card_font: "elegan", card_font_size: "besar", card_school_logo_pos: "kiri", card_library_logo_pos: "kanan", card_photo_pos: "kanan", card_qr_pos: "atas" }],
  ["putih-minimal", "Putih Minimalis", { card_theme: "light", card_layout: "modern", card_font: "mono", card_font_size: "kecil", card_school_logo_pos: "kiri", card_library_logo_pos: "kiri", card_photo_pos: "kiri", card_qr_pos: "bawah" }],
];
 fitur/laporan-kartu-belakang-cetak-duplex

export const uploadPhoto = async (file) => {
  if (file.size > 25 * 1024 * 1024) throw new Error("Ukuran foto maksimal 25MB");
  const fd = new FormData(); fd.append("file", file);
  const { data } = await api.post("/uploads/photo", fd);
  return data;
};

export const readFile = (file) => new Promise((resolve, reject) => {
  if (!file) return resolve("");
  if (file.size > 900 * 1024) return reject(new Error("Ukuran maksimal 900KB"));
  const r = new FileReader(); r.onload = () => resolve(r.result); r.onerror = reject; r.readAsDataURL(file);
});

 main
