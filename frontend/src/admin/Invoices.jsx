import { useEffect, useState } from 'react'
import { getInvoices } from '../api'

const CBMS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-700',
  synced: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

export default function Invoices() {
  const [invoices, setInvoices] = useState([])

  useEffect(() => {
    getInvoices().then(({ data }) => setInvoices(data.results ?? data)).catch(() => {})
  }, [])

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-800 mb-6">Invoices</h1>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Invoice #', 'Issued', 'Taxable (Rs)', 'VAT (Rs)', 'Total (Rs)', 'CBMS'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {invoices.map((inv) => (
              <tr key={inv.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono">{inv.invoice_no}</td>
                <td className="px-4 py-3 text-gray-500">{new Date(inv.issued_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">Rs {(inv.taxable_paisa / 100).toFixed(2)}</td>
                <td className="px-4 py-3">Rs {(inv.vat_paisa / 100).toFixed(2)}</td>
                <td className="px-4 py-3 font-medium">
                  Rs {((inv.taxable_paisa + inv.exempt_paisa + inv.vat_paisa) / 100).toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${CBMS_COLORS[inv.cbms_status] || ''}`}>
                    {inv.cbms_status}
                  </span>
                </td>
              </tr>
            ))}
            {invoices.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No invoices</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
