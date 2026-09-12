/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  envDir: import.meta.dirname ? `${import.meta.dirname}/..` : '..',
  envPrefix: ['VITE_', 'KAKAO_JS_'],
  plugins: [react()],
  server: {
    proxy: {
      '/routes': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
  },
})
