/**
 * Promise-based confirmation dialog replacing window.confirm.
 *
 *   const confirm = useConfirm()
 *   if (await confirm({ title: 'Void order?', message: 'All items will be removed.' })) { … }
 */
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

const ConfirmContext = createContext(null)

export function useConfirm() {
  const ctx = useContext(ConfirmContext)
  if (!ctx) throw new Error('useConfirm must be used inside <ConfirmProvider>')
  return ctx
}

export function ConfirmProvider({ children }) {
  const [dialog, setDialog] = useState(null)
  const resolveRef = useRef(null)

  const confirm = useCallback((opts) => {
    return new Promise((resolve) => {
      resolveRef.current = resolve
      setDialog({
        title: opts.title ?? 'Are you sure?',
        message: opts.message ?? '',
        confirmLabel: opts.confirmLabel ?? 'Confirm',
        cancelLabel: opts.cancelLabel ?? 'Cancel',
        danger: opts.danger ?? false,
      })
    })
  }, [])

  const close = useCallback((result) => {
    setDialog(null)
    resolveRef.current?.(result)
    resolveRef.current = null
  }, [])

  useEffect(() => {
    if (!dialog) return
    const onKey = (e) => {
      if (e.key === 'Escape') close(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [dialog, close])

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {dialog && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[90] p-4 animate-fade-in"
          onClick={() => close(false)}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            aria-label={dialog.title}
            className="glass w-full max-w-[420px] rounded-[24px] p-8 shadow-[0_20px_60px_rgba(0,0,0,0.2)] animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="font-sans font-black text-2xl text-text-primary mb-3 tracking-tight">{dialog.title}</h2>
            {dialog.message && (
              <p className="text-[15px] text-text-secondary font-medium mb-8 leading-relaxed">{dialog.message}</p>
            )}
            <div className="flex gap-4">
              <button
                autoFocus
                onClick={() => close(false)}
                className="flex-1 h-12 border-2 border-border bg-surface-active hover:bg-border rounded-xl text-text-secondary font-bold hover:text-text-primary transition-colors focus:ring-4 focus:ring-border/50 outline-none"
              >
                {dialog.cancelLabel}
              </button>
              <button
                onClick={() => close(true)}
                className={`flex-1 h-12 text-white rounded-xl font-bold shadow-md hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0 active:shadow-sm transition-all focus:ring-4 outline-none ${
                  dialog.danger
                    ? 'bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 focus:ring-rose-500/30'
                    : 'bg-gradient-to-r from-brand-primary to-brand-primaryHover focus:ring-brand-primary/30'
                }`}
              >
                {dialog.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  )
}
