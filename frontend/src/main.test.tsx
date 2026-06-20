import ReactDOM from 'react-dom/client'
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material'
import './index.css'

const theme = createTheme({
  palette: { primary: { main: '#1976d2' } },
})

function MinimalApp() {
  return (
    <div style={{ padding: 20 }}>
      <h1 style={{ color: '#1976d2' }}>✅ React + MUI 最小测试</h1>
      <p>如果你能看到这个页面，说明 React 和 MUI 基础功能正常</p>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <div style={{ background: '#e3f2fd', padding: 20, borderRadius: 8 }}>
          <h2>MUI 组件渲染区</h2>
          <p>这里应该有蓝色背景（来自 MUI CssBaseline）</p>
        </div>
      </ThemeProvider>
    </div>
  )
}

const root = document.getElementById('root')
if (!root) throw new Error('#root not found')

// NO StrictMode, NO BrowserRouter, minimal dependencies
ReactDOM.createRoot(root).render(<MinimalApp />)
