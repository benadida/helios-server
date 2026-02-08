import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  base: '/booth2026/',
  build: {
    outDir: 'dist',
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        manualChunks: () => 'booth',
        entryFileNames: 'booth.js',
        assetFileNames: 'booth.[ext]'
      }
    }
  },
  server: {
    port: 5173
  }
});
