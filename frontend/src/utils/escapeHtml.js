// HTML-escape untrusted text before it is interpolated into a markup string.
// Receipts and invoices are built as HTML strings and written into a print window
// via document.write; without this, operator-entered free text (product names,
// customer name/PAN, card-slip refs) is live markup and a value like
// `<img src=x onerror=...>` executes in that same-origin window (EF-02).
export function escapeHtml(value) {
  if (value === null || value === undefined) return ''
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
