import { formatBSDate } from '../utils/formatBSDate'
import { formatMoney } from '../utils/formatters'

const STORE_NAME = 'Everfresh Poultry'
const STORE_ADDRESS = 'Kathmandu, Nepal'
const STORE_PAN = '123456789'  // replace with actual PAN

function center(text, width = 32) {
  const pad = Math.max(0, Math.floor((width - text.length) / 2))
  return ' '.repeat(pad) + text
}

function divider(char = '-', width = 32) {
  return char.repeat(width)
}

/**
 * @param {object} opts
 * @param {object} opts.order  - created order object from API { id }
 * @param {Array}  opts.lines  - cart lines with product_name, tax_class, qty, uom, price_paisa, line_total_paisa
 * @param {string} opts.method - payment method
 * @param {number} opts.tenderedPaisa - cash tendered (paisa); 0 if non-cash
 * @param {string} [opts.outletName]
 * @param {string} [opts.ref]  - e-payment reference
 */
export function printReceipt({ order, lines, method, tenderedPaisa, outletName, ref }) {
  const now = new Date()
  const bsDate = formatBSDate(now, 'long')
  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
  const receiptNo = String(order?.id ?? '???').padStart(6, '0')

  const exemptPaisa  = lines.filter(l => l.tax_class !== 'taxable').reduce((s, l) => s + l.line_total_paisa, 0)
  const taxablePaisa = lines.filter(l => l.tax_class === 'taxable').reduce((s, l) => s + l.line_total_paisa, 0)
  const vatPaisa     = Math.floor((taxablePaisa * 13) / 100)
  const grandTotal   = exemptPaisa + taxablePaisa + vatPaisa
  const changePaisa  = method === 'cash' ? Math.max(0, (tenderedPaisa || grandTotal) - grandTotal) : 0

  const lineRows = lines.map((l) => {
    const qtyStr = `${l.qty} ${l.uom}`
    const price  = formatMoney(l.price_paisa)
    const total  = formatMoney(l.line_total_paisa)
    const vatTag = l.tax_class === 'taxable' ? '*' : ' '
    const name   = l.product_name.substring(0, 20)
    return `${vatTag}${name}\n  ${qtyStr} x ${price} = ${total}`
  }).join('\n')

  const methodLabel = { cash: 'Cash', card: 'Card', esewa: 'eSewa', khalti: 'Khalti' }[method] ?? method

  const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Receipt #${receiptNo}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Courier New', Courier, monospace;
    font-size: 12px;
    width: 80mm;
    margin: 0 auto;
    padding: 4mm 2mm;
    color: #000;
  }
  .center { text-align: center; }
  .right  { text-align: right; }
  .bold   { font-weight: bold; }
  .large  { font-size: 14px; }
  .small  { font-size: 10px; }
  .divider { border-top: 1px dashed #000; margin: 3mm 0; }
  .row    { display: flex; justify-content: space-between; }
  .vat-note { font-size: 10px; color: #555; margin-top: 2mm; }
  @media print {
    @page { size: 80mm auto; margin: 0; }
    body { padding: 2mm 2mm; }
  }
</style>
</head>
<body>
  <div class="center bold large">${STORE_NAME}</div>
  <div class="center small">${outletName ?? STORE_ADDRESS}</div>
  <div class="center small">PAN: ${STORE_PAN}</div>
  <div class="divider"></div>
  <div class="row"><span>Receipt #:</span><span class="bold">${receiptNo}</span></div>
  <div class="row"><span>Date:</span><span>${bsDate} ${timeStr}</span></div>
  <div class="divider"></div>
  <pre style="font-size:11px;white-space:pre-wrap;">${lineRows}</pre>
  <div class="small vat-note">* = VAT taxable item</div>
  <div class="divider"></div>
  ${exemptPaisa > 0  ? `<div class="row small"><span>Exempt</span><span>${formatMoney(exemptPaisa)}</span></div>` : ''}
  ${taxablePaisa > 0 ? `<div class="row small"><span>Taxable</span><span>${formatMoney(taxablePaisa)}</span></div>` : ''}
  ${vatPaisa > 0     ? `<div class="row small"><span>VAT 13%</span><span>${formatMoney(vatPaisa)}</span></div>` : ''}
  <div class="row bold large" style="margin-top:2mm;"><span>TOTAL</span><span>${formatMoney(grandTotal)}</span></div>
  <div class="divider"></div>
  <div class="row"><span>Payment</span><span>${methodLabel}${ref ? ` (${ref})` : ''}</span></div>
  ${method === 'cash' && tenderedPaisa ? `<div class="row"><span>Tendered</span><span>${formatMoney(tenderedPaisa)}</span></div>` : ''}
  ${changePaisa > 0 ? `<div class="row bold"><span>Change</span><span>${formatMoney(changePaisa)}</span></div>` : ''}
  <div class="divider"></div>
  <div class="center small" style="margin-top:3mm;">Thank you for shopping!</div>
  <div class="center small">Everfresh Fresh Every Day</div>
</body>
</html>`

  const win = window.open('', '_blank', 'width=340,height=600')
  if (!win) return
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => { win.print(); win.close() }, 300)
}
