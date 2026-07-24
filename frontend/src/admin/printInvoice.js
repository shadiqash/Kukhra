import { formatBSDate } from '../utils/formatBSDate'
import { formatMoney } from '../utils/formatters'
import { escapeHtml } from '../utils/escapeHtml'

const COMPANY_NAME    = 'Everfresh Poultry Pvt. Ltd.'
const COMPANY_ADDRESS = 'Kathmandu, Nepal'
const COMPANY_PAN     = '123456789'  // replace with actual PAN

/**
 * Render and print an IRD-format tax invoice.
 * @param {object} inv - Invoice object from API (with lines[], customer_name, customer_pan)
 */
export function printInvoice(inv) {
  const bsDate   = formatBSDate(inv.issued_at, 'long')
  const grandTotal = inv.total_paisa

  const lineRows = (inv.lines ?? []).map((l, i) => {
    const qty = l.qty_kg > 0
      ? `${parseFloat(l.qty_kg).toFixed(3)} kg`
      : `${l.qty_pieces} pcs`
    const taxLabel = l.tax_class === 'taxable' ? 'T' : 'E'
    // Prices are VAT-inclusive: line_total_paisa already contains the VAT.
    // "Amount" is the ex-VAT base; "Total" is the inclusive line total.
    const basePaisa = l.line_total_paisa - l.vat_paisa
    return `
      <tr>
        <td>${i + 1}</td>
        <td>${escapeHtml(l.product_name ?? l.product)}</td>
        <td class="center">${taxLabel}</td>
        <td class="right">${qty}</td>
        <td class="right">${formatMoney(l.unit_paisa)}</td>
        <td class="right">${formatMoney(basePaisa)}</td>
        <td class="right">${formatMoney(l.vat_paisa)}</td>
        <td class="right">${formatMoney(l.line_total_paisa)}</td>
      </tr>`
  }).join('')

  const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Invoice ${inv.invoice_number}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, sans-serif; font-size: 11px; color: #000; padding: 10mm 12mm; }
  h1 { font-size: 16px; margin-bottom: 1mm; }
  h2 { font-size: 13px; margin-bottom: 2mm; color: #333; text-align: center; }
  .header { display: flex; justify-content: space-between; margin-bottom: 6mm; }
  .company p, .invoice-meta p { margin-bottom: 1mm; line-height: 1.4; }
  .invoice-meta { text-align: right; }
  table { width: 100%; border-collapse: collapse; margin: 4mm 0; }
  th { background: #f3f3f3; border: 1px solid #ccc; padding: 2mm 3mm; text-align: left; font-size: 10px; }
  td { border: 1px solid #ddd; padding: 2mm 3mm; }
  .center { text-align: center; }
  .right  { text-align: right; }
  .totals { width: 60%; margin-left: 40%; border-collapse: collapse; margin-top: 3mm; }
  .totals td { padding: 1.5mm 3mm; border: none; }
  .totals tr.grand td { font-weight: bold; font-size: 12px; border-top: 2px solid #000; padding-top: 2mm; }
  .footer { margin-top: 8mm; font-size: 10px; color: #555; }
  .footer p { margin-bottom: 1mm; }
  .tax-note { font-size: 9px; color: #666; margin-top: 1mm; }
  @media print {
    @page { size: A4; margin: 0; }
    body { padding: 10mm 12mm; }
  }
</style>
</head>
<body>
  <h2>TAX INVOICE</h2>
  <div class="header">
    <div class="company">
      <h1>${COMPANY_NAME}</h1>
      <p>${COMPANY_ADDRESS}</p>
      <p><strong>PAN:</strong> ${COMPANY_PAN}</p>
    </div>
    <div class="invoice-meta">
      <p><strong>Invoice No:</strong> ${escapeHtml(inv.invoice_number)}</p>
      <p><strong>Date:</strong> ${bsDate}</p>
      ${inv.customer_name ? `<p><strong>Customer:</strong> ${escapeHtml(inv.customer_name)}</p>` : ''}
      ${inv.customer_pan  ? `<p><strong>Customer PAN:</strong> ${escapeHtml(inv.customer_pan)}</p>` : ''}
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Description</th>
        <th class="center">Tax</th>
        <th class="right">Qty</th>
        <th class="right">Unit Price</th>
        <th class="right">Amount</th>
        <th class="right">VAT</th>
        <th class="right">Total</th>
      </tr>
    </thead>
    <tbody>
      ${lineRows || '<tr><td colspan="8" style="text-align:center;color:#999">No line items</td></tr>'}
    </tbody>
  </table>
  <p class="tax-note">Tax column: T = Taxable (13% VAT), E = Exempt. Unit prices are inclusive of VAT; Amount shows the VAT-exclusive base.</p>

  <table class="totals">
    ${inv.exempt_paisa  > 0 ? `<tr><td>Exempt Amount</td><td class="right">${formatMoney(inv.exempt_paisa)}</td></tr>` : ''}
    ${inv.taxable_paisa > 0 ? `<tr><td>Taxable Amount</td><td class="right">${formatMoney(inv.taxable_paisa)}</td></tr>` : ''}
    ${inv.vat_paisa     > 0 ? `<tr><td>VAT (13%)</td><td class="right">${formatMoney(inv.vat_paisa)}</td></tr>` : ''}
    <tr class="grand">
      <td>Grand Total</td>
      <td class="right">${formatMoney(grandTotal)}</td>
    </tr>
  </table>

  <div class="footer">
    <p>This is a computer-generated invoice. No signature required.</p>
    <p>CBMS Status: ${escapeHtml(inv.cbms_status ?? '—')}</p>
  </div>
</body>
</html>`

  const win = window.open('', '_blank', 'width=794,height=1123')
  if (!win) return
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => { win.print(); win.close() }, 300)
}
