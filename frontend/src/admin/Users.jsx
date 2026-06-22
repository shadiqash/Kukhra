import { useEffect, useState } from 'react'
import { getUsers, createUser } from '../api'

const ROLES = ['cashier', 'manager', 'outlet_manager', 'warehouse', 'procurement', 'superuser']

export default function Users() {
  const [users, setUsers] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', role: 'cashier', password: '' })
  const [loading, setLoading] = useState(false)

  async function load() {
    getUsers().then(({ data }) => setUsers(data.results ?? data)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  async function handleSave(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await createUser(form)
      setShowForm(false)
      setForm({ username: '', email: '', role: 'cashier', password: '' })
      await load()
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">Users</h1>
        <button onClick={() => setShowForm(true)} className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700">
          + User
        </button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Username', 'Email', 'Role', 'Active'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{u.username}</td>
                <td className="px-4 py-3 text-gray-500">{u.email || '—'}</td>
                <td className="px-4 py-3 capitalize">{u.role}</td>
                <td className="px-4 py-3">{u.is_active ? '✓' : '—'}</td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No users</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold mb-4">New User</h2>
            <form onSubmit={handleSave} className="space-y-3">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input value={form.username} onChange={(e) => setForm({...form, username: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select value={form.role} onChange={(e) => setForm({...form, role: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">Cancel</button>
                <button type="submit" disabled={loading} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">{loading ? 'Saving…' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
