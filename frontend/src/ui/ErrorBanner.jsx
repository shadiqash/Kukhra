import { AlertCircle, RefreshCw } from 'lucide-react'

/** Inline load-failure banner for list screens, with a retry action. */
export default function ErrorBanner({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="flex items-center gap-3 bg-[#fef2f2] border-[1.5px] border-brand-danger/30 text-brand-danger rounded-lg px-4 py-3 mb-4 text-[14px]">
      <AlertCircle size={18} className="shrink-0" />
      <span className="flex-1">{typeof error === 'string' ? error : 'Failed to load data.'}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 font-semibold hover:underline shrink-0"
        >
          <RefreshCw size={14} /> Retry
        </button>
      )}
    </div>
  )
}
