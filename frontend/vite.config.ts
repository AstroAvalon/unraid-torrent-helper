import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // dev proxy to your backend in dev mode
      '/api': 'http://localhost:8088'
    }
  },
  build: {
    outDir: 'dist'
  }
})