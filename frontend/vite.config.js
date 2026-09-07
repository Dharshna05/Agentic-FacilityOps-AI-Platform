import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Vendor libraries change far less often than app code, so
        // splitting them into their own chunk means a browser that's
        // already cached recharts/framer-motion/lucide-react from a
        // previous visit doesn't re-download them just because app code
        // changed — this is what was behind the "chunk larger than
        // 500kB" build warning alongside the route-based lazy-loading in
        // App.jsx.
        manualChunks: {
          'vendor-charts': ['recharts'],
          'vendor-motion': ['framer-motion'],
          'vendor-icons': ['lucide-react'],
        },
      },
    },
  },
})
