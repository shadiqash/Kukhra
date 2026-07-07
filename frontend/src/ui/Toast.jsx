/**
 * Global toast notifications.
 *
 *   const toast = useToast()
 *   toast.success('Product saved')
 *   toast.error('Could not reach server')
 */
import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { CheckCircle2, AlertCircle, X } from 'lucide-react'

const ToastContext = createContext(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts((ts) => ts.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (kind, message) => {
      const id = ++idRef.current
      setToasts((ts) => [...ts.slice(-3), { id, kind, message }])
      setTimeout(() => dismiss(id), 4000)
    },
    [dismiss],
  )

  const api = useRef({
    success: (msg) => push('success', msg),
    error: (msg) => push('error', msg),
  })
  api.current.success = (msg) => push('success', msg)
  api.current.error = (msg) => push('error', msg)

  return (
    <ToastContext.Provider value={api.current}>
      {children}
      <div
        aria-live="polite"
        className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-[min(360px,calc(100vw-2rem))]"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`flex items-start gap-2.5 rounded-lg shadow-xl border-[1.5px] px-4 py-3 text-[14px] bg-white animate-[toast-in_.18s_ease-out] ${
              t.kind === 'success'
                ? 'border-brand-success/30 text-brand-success'
                : 'border-brand-danger/30 text-brand-danger'
            }`}
          >
            {t.kind === 'success' ? (
              <CheckCircle2 size={18} className="shrink-0 mt-0.5" />
            ) : (
              <AlertCircle size={18} className="shrink-0 mt-0.5" />
            )}
            <span className="flex-1 text-text-primary">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              aria-label="Dismiss"
              className="text-text-secondary hover:text-text-primary shrink-0 mt-0.5"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
