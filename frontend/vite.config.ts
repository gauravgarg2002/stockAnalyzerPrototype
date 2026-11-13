import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const target = process.env.VITE_API_TARGET ?? 'http://localhost:8080';
const proxy = { '/api': { target, changeOrigin: true } };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: true, proxy },
  preview: { port: 5173, host: true, proxy },
});
