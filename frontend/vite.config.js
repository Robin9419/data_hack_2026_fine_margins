import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// /api requests are forwarded to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    // Editors truncate a file before rewriting it; without this the dev server can cache the empty stylesheet.
    watch: { awaitWriteFinish: { stabilityThreshold: 150, pollInterval: 50 } },
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
