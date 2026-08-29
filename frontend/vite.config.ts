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
        // The interface, at the site root. This was the prototype at
        // /demo.html until its ideas had landed; it is the shipping one now.
        main: resolve(__dirname, 'index.html'),
        // The previous interface, kept reachable at /classic.html rather than
        // deleted: it still carries the AI assistant, which the new one does
        // not, and /demo.html links people already have redirect to the root.
        classic: resolve(__dirname, 'classic.html'),
      },
    },
  },
})
