import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5273,
    proxy: { '/api': { target: 'http://localhost:8600', changeOrigin: true, rewrite: p => p.replace(/^\/api/, '') } },
  },
});
