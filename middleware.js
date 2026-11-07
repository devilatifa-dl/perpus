// Vercel Routing Middleware: meneruskan /api/* ke backend.
//
// Cara pindah backend TANPA mengubah kode / push ulang:
//   Vercel -> Settings -> Environment Variables -> BACKEND_URL = https://<backend-anda>
//   lalu Redeploy. Env ini MENIMPA tujuan bawaan di vercel.json.
//
// - BACKEND_URL terisi  -> /api/* diteruskan ke BACKEND_URL (mis. backend Render).
// - BACKEND_URL kosong  -> diteruskan ke rewrite /api/* di vercel.json (backend cadangan),
//   sehingga situs tetap hidup walau env belum diisi.
export const config = { matcher: "/api/:path*" };

export default function middleware(request) {
  const backend = (process.env.BACKEND_URL || "").trim().replace(/\/+$/, "");
  if (!backend) {
    return new Response(null, { headers: { "x-middleware-next": "1" } });
  }
  const url = new URL(request.url);
  return new Response(null, { headers: { "x-middleware-rewrite": `${backend}${url.pathname}${url.search}` } });
}
