// cocoBI 前端静态服务器 - 零依赖,纯 Node.js stdlib
// 服务 dist/ 目录 + SPA fallback
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 4173;
const DIST_DIR = path.join(__dirname, 'dist');

console.log(`[cocoBI] Starting static server on 0.0.0.0:${PORT}`);
console.log(`[cocoBI] Serving from: ${DIST_DIR}`);

// 检查 dist 存在
if (!fs.existsSync(DIST_DIR)) {
  console.error(`[cocoBI] ERROR: dist/ not found at ${DIST_DIR}`);
  process.exit(1);
}

// MIME 类型
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

const server = http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0]; // 去掉 query
  let filePath = path.join(DIST_DIR, urlPath);

  // 安全检查:防止 ../
  if (!filePath.startsWith(DIST_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  // 默认 index.html
  if (urlPath === '/' || urlPath === '') {
    filePath = path.join(DIST_DIR, 'index.html');
  }

  // 文件存在?
  fs.stat(filePath, (err, stat) => {
    if (err || !stat.isFile()) {
      // SPA fallback: 返回 index.html
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

    // 读文件
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
