import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './App.css';

// 全局错误捕获,把错误直接渲染到页面,方便排查空白问题
window.addEventListener('error', (e) => {
  const root = document.getElementById('root');
  if (root && !root.innerHTML) {
    root.innerHTML = `
      <div style="padding:24px;font-family:monospace;color:#991b1b;background:#fef2f2;border:2px solid #fecaca;margin:24px;border-radius:8px;">
        <h2 style="margin-bottom:12px;">⚠️ JS 运行时错误</h2>
        <p><strong>${e.message}</strong></p>
        <pre style="background:#1f2937;color:#d1d5db;padding:12px;border-radius:6px;overflow:auto;font-size:12px;">${e.filename}:${e.lineno}:${e.colno}\n${e.error?.stack || ''}</pre>
      </div>
    `;
  }
});
window.addEventListener('unhandledrejection', (e) => {
  const root = document.getElementById('root');
  if (root && !root.innerHTML) {
    root.innerHTML = `
      <div style="padding:24px;font-family:monospace;color:#991b1b;background:#fef2f2;border:2px solid #fecaca;margin:24px;border-radius:8px;">
        <h2 style="margin-bottom:12px;">⚠️ Promise 错误</h2>
        <p><strong>${e.reason}</strong></p>
      </div>
    `;
  }
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
