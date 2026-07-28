// cocoBI 前端服务器 + API 反向代理
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { URL } = require('url');

const PORT = process.env.PORT || 4173;
const BACKEND_URL = process.env.BACKEND_URL || 'https://cocobi-backend-production.up.railway.app';

// 找 dist - 多种位置(包括 git 仓库)
const distCandidates = [
  path.join(__dirname, 'dist'),
  path.join(__dirname, '..', 'frontend', 'dist'),
  '/app/frontend/dist',
  '/app/dist',
  '/workspace/frontend/dist',
  '/workspace/dist',
  '/app/frontend',
  '/app',
];
let DIST_DIR = distCandidates.find((d) => fs.existsSync(path.join(d, 'index.html')));
if (!DIST_DIR) {
  // 尝试从 git 拉新 dist
  try {
    if (fs.existsSync('/app')) {
      console.log('[cocoBI] dist not found in candidates, trying git pull...');
      try {
        execSync('cd /app && git pull --ff-only 2>/dev/null', { stdio: 'ignore' });
      } catch (e) {}
      DIST_DIR = distCandidates.find((d) => fs.existsSync(path.join(d, 'index.html')));
    }
  } catch (e) {}
}
DIST_DIR = DIST_DIR || '/app/dist';

console.log(`[cocoBI] Starting server on 0.0.0.0:${PORT}`);
console.log(`[cocoBI] Static dir: ${DIST_DIR}`);
console.log(`[cocoBI] API proxy: ${BACKEND_URL}`);

if (!fs.existsSync(DIST_DIR)) {
  console.error(`[cocoBI] ERROR: dist/ not found. Tried: ${distCandidates.join(', ')}`);
  process.exit(1);
}

// 找 dist 里最新 index.html 的 script 文件名(强刷时 vite 会变 hash)
const indexHtml = fs.readFileSync(path.join(DIST_DIR, 'index.html'), 'utf-8');
const jsFileMatch = indexHtml.match(/src=["'](\/assets\/index-[^"']+\.js)["']/);
const cssFileMatch = indexHtml.match(/href=["'](\/assets\/index-[^"']+\.css)["']/);
console.log(`[cocoBI] Main JS: ${jsFileMatch ? jsFileMatch[1] : 'not found'}`);

if (!fs.existsSync(DIST_DIR)) {
  process.exit(1);
}

// MIME types
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

const SKIP_REQUEST_HEADERS = new Set([
  'host', 'connection', 'content-length', 'transfer-encoding',
]);

function proxyToBackend(req, res) {
  let targetUrl;
  try {
    targetUrl = new URL(req.url, BACKEND_URL);
  } catch (err) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Invalid backend URL', message: err.message }));
    return;
  }

  const isHttps = targetUrl.protocol === 'https:';
  const client = isHttps ? https : http;
  const options = {
    hostname: targetUrl.hostname,
    port: targetUrl.port || (isHttps ? 443 : 80),
    path: targetUrl.pathname + targetUrl.search,
    method: req.method,
    headers: { ...req.headers, host: targetUrl.host },
  };
  for (const h of SKIP_REQUEST_HEADERS) delete options.headers[h];
  if (options.headers['content-length']) {
    options.headers['content-length'] = Buffer.byteLength(req.body || '');
  }

  const proxyReq = client.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxyReq.on('error', (err) => {
    console.error('[cocoBI] proxy error:', err.message);
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Bad gateway', message: err.message }));
  });
  req.pipe(proxyReq);
}

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) {
    return proxyToBackend(req, res);
  }
  // 静态文件
  let filePath = path.join(DIST_DIR, req.url === '/' ? 'index.html' : req.url);
  if (!filePath.startsWith(DIST_DIR)) {
    res.writeHead(403);
    return res.end('Forbidden');
  }
  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      // SPA 路由 fallback
      filePath = path.join(DIST_DIR, 'index.html');
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[cocoBI] Ready on http://0.0.0.0:${PORT}`);
});
