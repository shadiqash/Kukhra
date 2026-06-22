import { useEffect, useState } from 'react'
import client from '../api/client'

export default function AuditLog() {
  const [entries, setEntries] = useState([])

  useEffect(() => {
    client.get('/audit-log/').then(({ data }) => setEntries(data.results ?? data)).catch(() => {})
  }, [])

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-800 mb-6">Audit Log</h1>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Time', 'User', 'Action', 'Object', 'Changes'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {entries.map((e, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                  {new Date(e.timestamp ?? e.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3">{e.user ?? e.actor}</td>
                <td className="px-4 py-3 capitalize">{e.action}</td>
                <td className="px-4 py-3 font-mono text-xs">{e.object_repr ?? e.object}</td>
                <td className="px-4 py-3 text-xs text-gray-500 font-mono truncate max-w-xs">
                  {e.changes ? JSON.stringify(e.changes) : '—'}
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No audit entries</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
