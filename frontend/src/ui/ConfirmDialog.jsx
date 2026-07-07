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
          className="fixed inset-0 bg-black/45 flex items-center justify-center z-[90] p-4"
          onClick={() => close(false)}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            aria-label={dialog.title}
            className="bg-white w-full max-w-[400px] rounded-[20px] shadow-xl p-7"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="font-sans font-bold text-[18px] text-text-primary mb-2">{dialog.title}</h2>
            {dialog.message && (
              <p className="text-[14px] text-text-secondary mb-6">{dialog.message}</p>
            )}
            <div className="flex gap-3">
              <button
                autoFocus
                onClick={() => close(false)}
                className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium hover:bg-brand-surface transition-colors"
              >
                {dialog.cancelLabel}
              </button>
              <button
                onClick={() => close(true)}
                className={`flex-1 h-11 text-white rounded-md font-semibold transition-colors ${
                  dialog.danger
                    ? 'bg-brand-danger hover:bg-[#991b1b]'
                    : 'bg-brand-primary hover:bg-brand-primaryHover'
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
