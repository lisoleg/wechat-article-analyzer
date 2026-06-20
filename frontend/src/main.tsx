import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import './index.css'

const theme = createTheme({ palette: { mode: 'light' } })

const root = document.getElementById('root')
if (root) {
  ReactDOM.createRoot(root).render(
    <React.Fragment>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </React.Fragment>,
  )
} else {
  console.error('[main.tsx] #root element not found!')
}
