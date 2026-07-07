import { useState } from 'react';
import { Plus } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import ErrorBanner from '../ui/ErrorBanner';
import { useToast } from '../ui/Toast';
import { getUsers, createUser, updateUser } from '../api';

const ROLE_BADGE = {
  superuser: 'bg-[#f3e8ff] text-[#7e22ce]',
  manager: 'bg-[#dbeafe] text-[#1d4ed8]',
  outlet_manager: 'bg-[#e0e7ff] text-[#3730a3]',
  cashier: 'bg-[#e0e7ff] text-[#4338ca]',
  warehouse: 'bg-[#f3f4f6] text-[#4b5563]',
};

export default function Users() {
  const toast = useToast();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ username: '', first_name: '', role: 'cashier', password: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [editingUser, setEditingUser] = useState(null);
  const [editForm, setEditForm] = useState({ first_name: '', last_name: '', role: 'cashier', is_active: true });
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState('');

  const { data: users, loading, error: loadError, refetch } = useApi(getUsers);

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createUser(form);
      setShowModal(false);
      setForm({ username: '', first_name: '', role: 'cashier', password: '' });
      toast.success('User created');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? JSON.stringify(err?.response?.data) ?? 'Failed to create user');
    } finally { setSaving(false); }
  }

  function openEdit(u) {
    setEditingUser(u);
    setEditForm({ first_name: u.first_name ?? '', last_name: u.last_name ?? '', role: u.role, is_active: u.is_active });
    setEditError('');
  }

  async function handleEditSave(e) {
    e.preventDefault();
    setEditSaving(true); setEditError('');
    try {
      await updateUser(editingUser.id, editForm);
      setEditingUser(null);
      toast.success('User updated');
      refetch();
    } catch (err) {
      setEditError(err?.response?.data?.detail ?? JSON.stringify(err?.response?.data) ?? 'Failed to update user');
    } finally { setEditSaving(false); }
  }

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={loadError} onRetry={refetch} />
      <div className="flex justify-between items-center mb-5 shrink-0">
        <h2 className="font-sans font-bold text-[18px] text-text-primary">User Management</h2>
        <button onClick={() => setShowModal(true)} className="h-10 px-4 bg-brand-primary text-white rounded-md font-sans font-semibold text-[14px] hover:bg-brand-primaryHover transition-colors flex items-center gap-2">
          <Plus size={16} /> User
        </button>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Username', 'Full Name', 'Role', 'Action'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-[#f0f0f0]">
                  {Array.from({ length: 4 }).map((__, j) => <td key={j} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>)}
                </tr>
              )) : users.map(u => (
                <tr key={u.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 text-text-primary font-medium">{u.username}</td>
                  <td className="px-4 py-3.5 text-text-primary">{u.first_name} {u.last_name}</td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium capitalize ${ROLE_BADGE[u.role] ?? 'bg-gray-100 text-gray-600'}`}>
                      {u.role?.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <button onClick={() => openEdit(u)} className="text-[13px] text-brand-primary hover:underline">Edit</button>
                  </td>
                </tr>
              ))}
              {!loading && users.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-10 text-center text-text-secondary text-[14px]">No users found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[480px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">Add User</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
            <form onSubmit={handleSave} className="flex flex-col gap-4">
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Username</label>
                <input required type="text" value={form.username} onChange={e => setForm({...form, username: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Full Name</label>
                  <input type="text" value={form.first_name} onChange={e => setForm({...form, first_name: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Role</label>
                  <select value={form.role} onChange={e => setForm({...form, role: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                    <option value="cashier">Cashier</option>
                    <option value="manager">Manager</option>
                    <option value="outlet_manager">Outlet Manager</option>
                    <option value="warehouse">Warehouse Worker</option>
                    <option value="procurement">Procurement</option>
                    <option value="superuser">Superuser</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Password</label>
                <input required type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 h-11 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{saving ? 'Saving…' : 'Save User'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingUser && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[480px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">Edit {editingUser.username}</h2>
            {editError && <p className="text-brand-danger text-[13px] mb-3">{editError}</p>}
            <form onSubmit={handleEditSave} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">First Name</label>
                  <input type="text" value={editForm.first_name} onChange={e => setEditForm({...editForm, first_name: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Last Name</label>
                  <input type="text" value={editForm.last_name} onChange={e => setEditForm({...editForm, last_name: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Role</label>
                <select value={editForm.role} onChange={e => setEditForm({...editForm, role: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="cashier">Cashier</option>
                  <option value="manager">Manager</option>
                  <option value="outlet_manager">Outlet Manager</option>
                  <option value="warehouse">Warehouse Worker</option>
                  <option value="procurement">Procurement</option>
                  <option value="superuser">Superuser</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-[13px] text-text-secondary">
                <input type="checkbox" checked={editForm.is_active} onChange={e => setEditForm({...editForm, is_active: e.target.checked})} />
                Active
              </label>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => setEditingUser(null)} className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={editSaving} className="flex-1 h-11 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{editSaving ? 'Saving…' : 'Save Changes'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
