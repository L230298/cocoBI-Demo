// cocoBI 前端服务器 + API 反向代理
// - 服务 dist/ 静态文件
// - 代理 /api/* 请求到后端
// - 同时支持 http 和 https 后端
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const PORT = process.env.PORT || 4173;
const DIST_DIR = path.join(__dirname, 'dist');
const BACKEND_URL = process.env.BACKEND_URL || 'https://cocobi-backend-production.up.railway.app';

console.log(`[cocoBI] Starting server on 0.0.0.0:${PORT}`);
console.log(`[cocoBI] Static dir: ${DIST_DIR}`);
console.log(`[cocoBI] API proxy: ${BACKEND_URL}`);

if (!fs.existsSync(DIST_DIR)) {
  console.error(`[cocoBI] ERROR: dist/ not found at ${DIST_DIR}`);
  process.exit(1);
}

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

// 跳过代理的请求头(由 http.request 自动生成)
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

  console.log(`[PROXY] ${req.method} ${req.url} -> ${targetUrl.href}`);

  // 根据后端协议选择 http 或 https
  const lib = targetUrl.protocol === 'https:' ? https : http;

  // 过滤请求头
  const headers = {};
  for (const [k, v] of Object.entries(req.headers)) {
    if (!SKIP_REQUEST_HEADERS.has(k.toLowerCase())) {
      headers[k] = v;
    }
  }
  headers['host'] = targetUrl.host;
  headers['x-forwarded-for'] = req.socket.remoteAddress || '';
  headers['x-forwarded-proto'] = 'https';

  const proxyReq = lib.request(
    {
      hostname: targetUrl.hostname,
      port: targetUrl.port || (targetUrl.protocol === 'https:' ? 443 : 80),
      path: targetUrl.pathname + targetUrl.search,
      method: req.method,
      headers,
    },
    (proxyRes) => {
      // 删除 hop-by-hop 头
      const responseHeaders = { ...proxyRes.headers };
      delete responseHeaders['transfer-encoding'];
      delete responseHeaders['connection'];
      res.writeHead(proxyRes.statusCode, responseHeaders);
      proxyRes.pipe(res);
    }
  );

  proxyReq.on('error', (err) => {
    console.error(`[PROXY ERROR] ${req.url} -> ${err.message}`);
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Bad Gateway', message: err.message, target: BACKEND_URL }));
    }
  });

  // 转发请求 body
  req.pipe(proxyReq);
}

const server = http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0];

  // /api/* 代理到后端
  if (urlPath.startsWith('/api/') || urlPath === '/api') {
    proxyToBackend(req, res);
    return;
  }

  // 否则服务静态文件
  let filePath = path.join(DIST_DIR, urlPath);

  // 安全检查
  if (!filePath.startsWith(DIST_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  // 根路径 → index.html
  if (urlPath === '/' || urlPath === '') {
    filePath = path.join(DIST_DIR, 'index.html');
  }

  fs.stat(filePath, (err, stat) => {
    if (err || !stat.isFile()) {
      // SPA fallback
      const indexPath = path.join(DIST_DIR, 'index.html');
      fs.readFile(indexPath, (e, content) => {
        if (e) {
          res.writeHead(500);
          res.end('Internal Server Error');
          return;
        }
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(content);
      });
      return;
    }

    fs.readFile(filePath, (e, content) => {
      if (e) {
        res.writeHead(500);
        res.end('Internal Server Error');
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      const mime = MIME[ext] || 'application/octet-stream';
      res.writeHead(200, { 'Content-Type': mime });
      res.end(content);
    });
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[cocoBI] Listening on http://0.0.0.0:${PORT}`);
});

server.on('error', (err) => {
  console.error(`[cocoBI] Server error: ${err.message}`);
  process.exit(1);
});
