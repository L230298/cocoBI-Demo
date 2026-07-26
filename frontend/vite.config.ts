import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // 监听所有网络接口,允许手机/局域网访问
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        // 使用 IPv4 避免 Vite 代理在 Windows 上的 localhost 解析问题
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
