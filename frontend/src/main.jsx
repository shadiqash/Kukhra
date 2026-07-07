import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import ErrorBoundary from './ui/ErrorBoundary'
import { ToastProvider } from './ui/Toast'
import { ConfirmProvider } from './ui/ConfirmDialog'
import App from './App'
import './index.css'

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <HashRouter>
        <AuthProvider>
          <ToastProvider>
            <ConfirmProvider>
              <App />
            </ConfirmProvider>
          </ToastProvider>
        </AuthProvider>
      </HashRouter>
    </ErrorBoundary>
  </React.StrictMode>
)
