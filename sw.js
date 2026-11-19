/* 天书劫 4.0 网页版 —— 分片拼装 Service Worker
 * game.data 共 93.8MB，超过 GitHub 网页单文件 25MB 上传上限，
 * 因此切成 4 个 < 25MB 的分片提交到仓库，由本 SW 在加载时拼回整包。
 */
const PARTS = ['game.data.001', 'game.data.002', 'game.data.003', 'game.data.004'];

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

async function buildData() {
  const bufs = [];
  for (const p of PARTS) {
    const r = await fetch(new URL(p, self.registration.scope).href, { cache: 'force-cache' });
    if (!r.ok) throw new Error('part ' + p + ' HTTP ' + r.status);
    bufs.push(await r.arrayBuffer());
  }
  const total = bufs.reduce((a, b) => a + b.byteLength, 0);
  const out = new Uint8Array(total);
  let off = 0;
  for (const b of bufs) {
    out.set(new Uint8Array(b), off);
    off += b.byteLength;
  }
  return new Response(out, {
    status: 200,
    headers: {
      'Content-Type': 'application/octet-stream',
      'Content-Length': String(total),
      'Cache-Control': 'no-store'
    }
  });
}

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (!url.pathname.endsWith('/game.data')) return;
  e.respondWith(buildData());
});
