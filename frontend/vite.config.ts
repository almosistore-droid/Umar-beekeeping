import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Allow opening the dev server through a temporary HTTPS tunnel (for testing inside Telegram)
    allowedHosts: ['localhost', '.trycloudflare.com', '.ngrok-free.app'],
    // In Docker on Windows/macOS file changes from `git pull` don't reach the container as events;
    // polling makes Vite notice them instead of serving the old screens from memory.
    watch: process.env.VITE_POLL === '1' ? { usePolling: true, interval: 1000 } : undefined,
    proxy: {
      '/api': { target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: { target: 'es2020', sourcemap: false },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
