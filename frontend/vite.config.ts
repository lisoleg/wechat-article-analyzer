import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  },
  build: {
    manifest: true,   // 生成 manifest.json，方便 index.html 找到真实 bundle 文件名
    rollupOptions: {
      output: {
        // 固定 entry 文件名（不含 hash），简化 index.html 的引用
        entryFileNames: 'assets/index.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]',
      },
    },
  },
  optimizeDeps: {
    // MUI + emotion 在 Vite 预构建中有已知兼容性问题
    // 排除它们让浏览器直接加载原生 ESM 模块
    exclude: [
      '@mui/material',
      '@mui/icons-material',
      '@emotion/react',
      '@emotion/styled',
    ],
    include: [
      'react-router-dom',
    ],
  },
  define: {
    'process.env': {},
    global: 'globalThis',
  },
})
