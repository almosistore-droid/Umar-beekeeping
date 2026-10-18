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
  build: {
    target: 'es2020',
    sourcemap: false,
    rollupOptions: {
      output: {
        // libraries change rarely: kept in their own files, phones keep them cached across our releases
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return undefined
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'react'
          if (id.includes('react-router')) return 'router'
          if (id.includes('@tanstack') || id.includes('idb-keyval')) return 'query'
          return undefined
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
