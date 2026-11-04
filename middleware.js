// Vercel Routing Middleware: meneruskan /api/* ke backend dari env BACKEND_URL (tanpa hardcode URL).
export const config = { matcher: "/api/:path*" };

export default function middleware(request) {
  const backend = (process.env.BACKEND_URL || "").replace(/\/+$/, "");
  if (!backend) {
    return new Response(JSON.stringify({ detail: "BACKEND_URL belum diisi di Vercel (Settings → Environment Variables)" }), { status: 500, headers: { "content-type": "application/json" } });
  }
  const url = new URL(request.url);
  return new Response(null, { headers: { "x-middleware-rewrite": `${backend}${url.pathname}${url.search}` } });
}
