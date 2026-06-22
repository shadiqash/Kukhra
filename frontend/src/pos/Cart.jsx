export default function Cart({ lines, onRemove, onQtyChange }) {
  const total = lines.reduce((s, l) => s + l.line_total_paisa, 0)

  if (lines.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
        Cart is empty
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
      {lines.map((line, idx) => (
        <div key={idx} className="flex items-center gap-2 py-2 px-1">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{line.product_name}</p>
            <p className="text-xs text-gray-500">
              Rs {(line.price_paisa / 100).toFixed(2)} / {line.uom}
            </p>
          </div>
          <input
            type="number"
            min="0.1"
            step="0.1"
            value={line.qty}
            onChange={(e) => onQtyChange(idx, parseFloat(e.target.value) || 0)}
            className="w-16 border border-gray-200 rounded px-1 py-0.5 text-sm text-center"
          />
          <span className="w-20 text-right text-sm font-medium">
            Rs {(line.line_total_paisa / 100).toFixed(2)}
          </span>
          <button
            onClick={() => onRemove(idx)}
            className="text-gray-400 hover:text-red-500 text-lg leading-none"
          >
            ×
          </button>
        </div>
      ))}
      <div className="flex justify-between items-center pt-3 pb-1 px-1 font-bold text-base">
        <span>Total</span>
        <span>Rs {(total / 100).toFixed(2)}</span>
      </div>
    </div>
  )
}
