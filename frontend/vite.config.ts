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
    include: [
      '@emotion/react/jsx-runtime',
      '@emotion/react',
      '@emotion/styled',
      '@mui/material',
      '@mui/material/Box',
      '@mui/material/Typography',
      '@mui/material/AppBar',
      '@mui/material/Toolbar',
      '@mui/material/Button',
      '@mui/material/Paper',
      '@mui/material/Grid',
      '@mui/material/TextField',
      '@mui/material/FormControl',
      '@mui/material/InputLabel',
      '@mui/material/Select',
      '@mui/material/MenuItem',
      '@mui/material/Tab',
      '@mui/material/Tabs',
      '@mui/material/Table',
      '@mui/material/TableBody',
      '@mui/material/TableCell',
      '@mui/material/TableContainer',
      '@mui/material/TableHead',
      '@mui/material/TableRow',
      '@mui/material/IconButton',
      '@mui/material/Divider',
      '@mui/material/Drawer',
      '@mui/material/List',
      '@mui/material/ListItem',
      '@mui/material/ListItemButton',
      '@mui/material/ListItemIcon',
      '@mui/material/ListItemText',
      '@mui/icons-material',
      'react-router-dom',
    ],
  },
  define: {
    'process.env': {},
    global: 'globalThis',
  },
})
