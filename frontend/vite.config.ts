/// <reference types="vitest/config" />
import vue from '@vitejs/plugin-vue'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), 'VITE_'), ...process.env }
  return {
    plugins: [vue()],
    server: {
      // Same-origin API calls: the dev server proxies /api to the backend container.
      proxy: {
        '/api': { target: env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000', changeOrigin: false },
      },
    },
    test: {
      environment: 'jsdom',
      include: ['tests/**/*.spec.ts'],
      setupFiles: ['tests/setup.ts'],
    },
  }
})
