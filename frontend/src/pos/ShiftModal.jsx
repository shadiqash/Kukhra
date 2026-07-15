import { useState } from 'react'
import { openSession, closeSession, getSessionSummary } from '../api'
import { formatDateTimeString, formatMoney } from '../utils/formatters'

const METHOD_LABELS = { cash: 'Cash', card: 'Card', esewa: 'eSewa', khalti: 'Khalti' }

export default function ShiftModal({ session, counterId, onOpen, onClose, onDismiss }) {
  const [float, setFloat] = useState('')
  const [counted, setCounted] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [zReport, setZReport] = useState(null)

  async function handleOpen(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { data } = await openSession({
        counter: counterId,
        opening_float_paisa: Math.round(parseFloat(float) * 100),
      })
      // Null guard: opened_at should be set by the server; fall back to now
      if (!data.opened_at) data.opened_at = new Date().toISOString()
      onOpen(data)
    } catch {
      setError('Failed to open shift')
    } finally {
      setLoading(false)
    }
  }

  async function handleClose(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await closeSession(session.id, {
        closing_counted_paisa: Math.round(parseFloat(counted) * 100),
      })
      const { data: summary } = await getSessionSummary(session.id)
      setZReport(summary)
    } catch {
      setError('Failed to close shift')
    } finally {
      setLoading(false)
    }
  }

  function handleZReportDone() {
    setZReport(null)
    onClose()
  }

  if (zReport) {
    // Blind count: the server withholds the drawer audit from cashiers, so these
    // fields are simply absent for them. Only a manager closing a till sees them.
    const variance = zReport.variance_paisa
    const showsAudit = variance !== undefined && variance !== null
    const varianceColor = variance === 0
      ? 'text-brand-primary'
      : variance > 0 ? 'text-blue-700' : 'text-brand-danger'

    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold">Z-Report</h2>
            <span className="text-xs text-text-secondary/70">
              {formatDateTimeString(zReport.closed_at ?? new Date().toISOString())}
            </span>
          </div>

          <div className="space-y-1 text-sm">
            <Row label="Opening Float" value={formatMoney(zReport.opening_float_paisa)} />
            <div className="border-t border-brand-border/60 my-2" />
            <Row label="Total Sales" value={`${zReport.sales_count} orders`} />
            <Row label="Sales Amount" value={formatMoney(zReport.sales_total_paisa)} bold />
            <div className="border-t border-brand-border/60 my-2" />
            <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-1">By Method</p>
            {zReport.payment_breakdown.length === 0 ? (
              <p className="text-text-secondary/70 text-xs">No payments</p>
            ) : (
              zReport.payment_breakdown.map((row) => (
                <Row
                  key={row.method}
                  label={METHOD_LABELS[row.method] ?? row.method}
                  value={`${formatMoney(row.total)} (${row.count})`}
                />
              ))
            )}
            {showsAudit ? (
              <>
                <div className="border-t border-brand-border/60 my-2" />
                <Row label="Counted Cash" value={formatMoney(zReport.closing_counted_paisa)} />
                <Row label="Expected Cash" value={formatMoney(zReport.expected_cash_paisa)} />
                <div className={`flex justify-between font-semibold pt-1 ${varianceColor}`}>
                  <span>Variance</span>
                  <span>
                    {variance >= 0 ? '+' : ''}{formatMoney(Math.abs(variance))}
                    {variance > 0 ? ' over' : variance < 0 ? ' short' : ' balanced'}
                  </span>
                </div>
              </>
            ) : (
              <>
                <div className="border-t border-brand-border/60 my-2" />
                <p className="text-xs text-text-secondary/70">
                  Drawer counted and submitted. Your manager reviews the reconciliation.
                </p>
              </>
            )}
          </div>

          <div className="flex gap-2 mt-5">
            <button
              onClick={() => window.print()}
              className="flex-1 border border-brand-border text-text-secondary py-2 rounded-lg text-sm"
            >
              Print
            </button>
            <button
              onClick={handleZReportDone}
              className="flex-1 bg-brand-primary hover:bg-brand-primaryHover text-white py-2 rounded-lg text-sm font-semibold"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        {!session ? (
          <>
            <h2 className="text-lg font-bold mb-4">Open Shift</h2>
            {error && <p className="text-brand-danger text-sm mb-3">{error}</p>}
            <form onSubmit={handleOpen} className="space-y-3">
              <div>
                <label className="text-sm font-medium text-text-primary">Opening Float (Rs)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={float}
                  onChange={(e) => setFloat(e.target.value)}
                  required
                  className="w-full border border-brand-border rounded-lg px-3 py-2 text-sm mt-1 focus:border-brand-primary focus:outline-none"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={onDismiss} className="flex-1 border border-brand-border text-text-secondary py-2 rounded-lg text-sm">
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="flex-1 bg-brand-primary hover:bg-brand-primaryHover text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">
                  {loading ? 'Opening…' : 'Open Shift'}
                </button>
              </div>
            </form>
          </>
        ) : (
          <>
            <h2 className="text-lg font-bold mb-1">Close Shift</h2>
            <p className="text-sm text-text-secondary mb-4">
              Float opened: {formatMoney(session.opening_float_paisa)}
              {session.opened_at && (
                <span className="ml-2">@ {formatDateTimeString(session.opened_at)}</span>
              )}
            </p>
            {error && <p className="text-brand-danger text-sm mb-3">{error}</p>}
            <form onSubmit={handleClose} className="space-y-3">
              <div>
                <label className="text-sm font-medium text-text-primary">Counted Cash (Rs)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={counted}
                  onChange={(e) => setCounted(e.target.value)}
                  required
                  className="w-full border border-brand-border rounded-lg px-3 py-2 text-sm mt-1 focus:border-brand-primary focus:outline-none"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={onDismiss} className="flex-1 border border-brand-border text-text-secondary py-2 rounded-lg text-sm">
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="flex-1 bg-brand-danger hover:bg-[#991b1b] text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">
                  {loading ? 'Closing…' : 'Close Shift'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

function Row({ label, value, bold }) {
  return (
    <div className={`flex justify-between ${bold ? 'font-semibold' : 'text-text-primary'}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  )
}
