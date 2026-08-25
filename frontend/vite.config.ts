import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    strictPort: false,
  },
  build: {
    rollupOptions: {
      input: {
        // The shipping app.
        main: resolve(__dirname, 'index.html'),
        // The design prototype, at /demo.html. Separate entry so it can be
        // worked on without touching the live interface, and dropped in one
        // line once its ideas have either landed or been rejected.
        demo: resolve(__dirname, 'demo.html'),
      },
    },
  },
})
