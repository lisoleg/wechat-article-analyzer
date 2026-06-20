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
    // MUI + emotion 的官方推荐 Vite 配置
    // 只预构建顶层包（不含子路径如 /jsx-runtime），避免 init_emotion 错误
    // 同时包含 hoist-non-react-statics 解决 CJS/ESM default export 兼容性
    include: [
      '@mui/material',
      '@mui/icons-material',
      '@emotion/react',
      '@emotion/styled',
      'hoist-non-react-statics',       // ← 关键：CJS 模块必须预构建才能提供 default export
      'react-router-dom',
    ],
  },
  define: {
    'process.env': {},
    global: 'globalThis',
  },
})
