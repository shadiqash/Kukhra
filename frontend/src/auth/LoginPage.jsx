import { useState } from 'react';
import { useAuth } from './AuthContext';
import { usePageTitle } from '../hooks/usePageTitle';
import { Eye, EyeOff, AlertTriangle } from 'lucide-react';
import logoIcon from '../assets/logo-icon.png';

export default function LoginPage() {
  usePageTitle('Sign in');
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
    } catch {
      setError('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex w-full bg-brand-surface font-sans">
      {/* Left Half - Hero (Desktop only) */}
      <div className="hidden lg:flex lg:w-1/2 bg-brand-primary relative flex-col items-center justify-center overflow-hidden">
        {/* Subtle texture or pattern placeholder */}
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-white to-transparent mix-blend-overlay"></div>
        <div className="z-10 flex flex-col items-center">
          <img src={logoIcon} alt="Everfresh" width="112" height="112" className="mb-4" />
          <h1 className="text-white font-bold text-[28px] tracking-wide mb-2">Everfresh Poultry</h1>
          <p className="text-white/60 text-lg">Fresh Every Day</p>
        </div>
      </div>

      {/* Right Half - Login Card */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-4">
        <div className="w-full max-w-[400px] bg-white rounded-xl shadow-md p-8 border border-brand-border">
          <h2 className="text-text-primary font-semibold text-2xl mb-1">Welcome back</h2>
          <p className="text-text-secondary text-sm mb-8">Sign in to continue</p>
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
                autoFocus
                className="w-full h-12 border-[1.5px] border-brand-border rounded-md px-4 text-[15px] focus:outline-none focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 transition-shadow"
              />
            </div>
            
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full h-12 border-[1.5px] border-brand-border rounded-md pl-4 pr-10 text-[15px] focus:outline-none focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 transition-shadow"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-brand-primary hover:bg-brand-primaryHover text-white font-semibold text-[15px] rounded-md transition-colors flex items-center justify-center mt-2 disabled:opacity-70"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                'Sign In'
              )}
            </button>
            
            {error && (
              <div className="flex items-center gap-2 bg-red-50 text-brand-danger text-[13px] px-3 py-2 rounded-full border border-red-100 justify-center">
                <AlertTriangle size={14} />
                <span>{error}</span>
              </div>
            )}
          </form>

          <div className="mt-8 text-center text-text-secondary text-[12px]">
            Everfresh Poultry Pvt. Ltd. · Kathmandu
          </div>
        </div>
      </div>
    </div>
  );
}
