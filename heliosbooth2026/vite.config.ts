import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  base: '/booth2026/',
  build: {
    outDir: 'dist',
    // Ensure single bundle for offline operation
    cssCodeSplit: false,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        verify: resolve(__dirname, 'verify.html')
      },
      output: {
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]'
      }
    },
    // Generate sourcemaps for debugging
    sourcemap: true,
    // Minify for production
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: false, // Keep console for debugging crypto issues
        drop_debugger: true
      }
    }
  },
  server: {
    port: 5173,
    // Proxy API requests to Django during development
    proxy: {
      '/helios': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  // Copy static assets
  publicDir: 'public'
});
