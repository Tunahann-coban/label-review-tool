import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api requests are forwarded to the FastAPI service
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
