// Vercel Routing Middleware: meneruskan /api/* ke backend.
// - Jika env BACKEND_URL diisi di Vercel → /api/* diteruskan ke BACKEND_URL (mis. backend Render).
// - Jika kosong → diteruskan ke langkah berikutnya, yaitu rewrite /api/* di vercel.json
//   (backend produksi Emergent). Dengan begitu situs tidak pernah mati hanya karena env belum diisi.
export const config = { matcher: "/api/:path*" };

export default function middleware(request) {
  const backend = (process.env.BACKEND_URL || "").trim().replace(/\/+$/, "");
  if (!backend) {
    return new Response(null, { headers: { "x-middleware-next": "1" } });
  }
  const url = new URL(request.url);
  return new Response(null, { headers: { "x-middleware-rewrite": `${backend}${url.pathname}${url.search}` } });
}
