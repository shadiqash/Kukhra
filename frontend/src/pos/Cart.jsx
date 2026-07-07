import { formatMoney } from '../utils/formatters'

export default function Cart({ lines, onRemove, onQtyChange }) {
  if (lines.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-secondary/70 text-sm">
        Cart is empty
      </div>
    )
  }

  const exemptPaisa = lines
    .filter((l) => l.tax_class !== 'taxable')
    .reduce((s, l) => s + l.line_total_paisa, 0)
  const taxablePaisa = lines
    .filter((l) => l.tax_class === 'taxable')
    .reduce((s, l) => s + l.line_total_paisa, 0)
  const vatPaisa = Math.floor((taxablePaisa * 13) / 100)
  const grandTotal = exemptPaisa + taxablePaisa + vatPaisa

  return (
    <div className="flex-1 overflow-y-auto flex flex-col">
      <div className="divide-y divide-brand-border/60 flex-1">
        {lines.map((line, idx) => (
          <div key={idx} className="flex items-center gap-2 py-2 px-1">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{line.product_name}</p>
              <p className="text-xs text-text-secondary">
                {formatMoney(line.price_paisa)} / {line.uom}
                {line.tax_class === 'taxable' && (
                  <span className="ml-1 text-amber-600 font-medium">+VAT</span>
                )}
              </p>
            </div>
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={line.qty}
              onChange={(e) => onQtyChange(idx, parseFloat(e.target.value) || 0)}
              className="w-16 border border-brand-border rounded px-1 py-0.5 text-sm text-center"
            />
            <span className="w-20 text-right text-sm font-medium">
              {formatMoney(line.line_total_paisa)}
            </span>
            <button
              onClick={() => onRemove(idx)}
              className="text-text-secondary hover:text-brand-danger text-lg leading-none"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Tax breakdown */}
      <div className="border-t border-brand-border pt-2 px-1 mt-1 text-xs space-y-1">
        {exemptPaisa > 0 && (
          <div className="flex justify-between text-text-secondary">
            <span>Exempt</span>
            <span>{formatMoney(exemptPaisa)}</span>
          </div>
        )}
        {taxablePaisa > 0 && (
          <div className="flex justify-between text-text-secondary">
            <span>Taxable</span>
            <span>{formatMoney(taxablePaisa)}</span>
          </div>
        )}
        {vatPaisa > 0 && (
          <div className="flex justify-between text-amber-700 font-medium">
            <span>VAT (13%)</span>
            <span>{formatMoney(vatPaisa)}</span>
          </div>
        )}
        <div className="flex justify-between font-bold text-sm text-text-primary border-t border-brand-border pt-1 mt-1">
          <span>Grand Total</span>
          <span>{formatMoney(grandTotal)}</span>
        </div>
      </div>
    </div>
  )
}
