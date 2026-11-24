import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import basicSsl from '@vitejs/plugin-basic-ssl'

// npm run dev        -> http://localhost:5173 (proxy a Django en :8000)
// npm run dev:https  -> https://<ip-del-pc>:5173 (necesario para usar la cámara desde el celular)
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon-192.png', 'apple-touch-icon.png', 'logo-ilux.png', 'logo-ilux-inverso.png', 'marca-ilux.png'],
      manifest: {
        name: 'ILUX SCM – Control de Materiales',
        short_name: 'ILUX SCM',
        description: 'Remisiones digitales de materiales, herramientas y equipos',
        lang: 'es-CO',
        theme_color: '#FFFFFF',
        background_color: '#F3F3F0',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api/, /^\/admin/, /^\/static/],
        globPatterns: ['**/*.{js,css,html,png,svg,woff2,webmanifest}'],
      },
    }),
    mode === 'https' ? basicSsl() : null,
  ].filter(Boolean),
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/admin': 'http://127.0.0.1:8000',
      '/static': 'http://127.0.0.1:8000',
    },
  },
}))
