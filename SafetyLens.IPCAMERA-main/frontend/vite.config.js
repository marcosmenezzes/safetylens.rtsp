import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Reutiliza as fotos institucionais sem duplicá-las dentro do frontend.
  publicDir: '../static',
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      // Mantém frontend e backend equivalentes à mesma origem durante o desenvolvimento.
      '/api': 'http://127.0.0.1:5050',
      '/image': 'http://127.0.0.1:5050',
    },
  },
})
