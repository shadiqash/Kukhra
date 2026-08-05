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
    <div className="min-h-screen flex w-full bg-background font-sans transition-colors duration-500">
      {/* Left Half - Hero (Desktop only) */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-brand-primary to-brand-primaryHover relative flex-col items-center justify-center overflow-hidden">
        {/* Subtle texture or pattern placeholder */}
        <div className="absolute inset-0 opacity-20 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-white/30 to-transparent mix-blend-overlay animate-pulse-subtle"></div>
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10"></div>
        <div className="z-10 flex flex-col items-center relative hover:scale-105 transition-transform duration-700 ease-out">
          <div className="w-28 h-28 bg-white/10 backdrop-blur-md rounded-[32px] p-4 flex items-center justify-center shadow-[0_0_40px_rgba(255,255,255,0.1)] border border-white/20 mb-6">
            <img src={logoIcon} alt="Everfresh" width="80" height="80" className="drop-shadow-lg" />
          </div>
          <h1 className="text-white font-black text-4xl tracking-tight mb-2 drop-shadow-md">Everfresh</h1>
          <p className="text-white/80 text-lg font-medium tracking-wide">Fresh Every Day</p>
        </div>
      </div>

      {/* Right Half - Login Card */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 relative overflow-hidden">
        {/* Decorative background blobs for the right side */}
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-brand-primary/5 blur-[100px] pointer-events-none"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[400px] h-[400px] rounded-full bg-brand-secondary/5 blur-[80px] pointer-events-none"></div>
        
        <div className="w-full max-w-[420px] glass rounded-[32px] p-10 relative z-10 animate-slide-up">
          <div className="lg:hidden flex justify-center mb-8">
            <div className="w-16 h-16 bg-brand-primary/10 rounded-2xl p-3 flex items-center justify-center">
              <img src={logoIcon} alt="Everfresh" width="40" height="40" />
            </div>
          </div>
          
          <h2 className="text-text-primary font-bold text-3xl mb-2 tracking-tight">Welcome back</h2>
          <p className="text-text-muted text-[15px] font-medium mb-10">Sign in to your account</p>
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            <div>
              <label className="block text-sm font-semibold text-text-secondary mb-2 pl-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
                autoFocus
                className="inp h-14 bg-surface-active"
              />
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-text-secondary mb-2 pl-1">Password</label>
              <div className="relative group">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="inp h-14 bg-surface-active pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-text-muted hover:text-brand-primary transition-colors focus:outline-none"
                >
                  {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-14 bg-gradient-to-r from-brand-primary to-brand-primaryHover text-white font-bold text-[16px] rounded-xl transition-all shadow-md hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center mt-4 disabled:opacity-70 disabled:hover:scale-100 disabled:shadow-none"
            >
              {loading ? (
                <div className="w-6 h-6 border-[3px] border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                'Sign In'
              )}
            </button>
            
            {error && (
              <div className="flex items-center gap-2 bg-brand-danger/10 text-brand-danger font-semibold text-sm px-4 py-3 rounded-xl border border-brand-danger/20 justify-center animate-fade-in">
                <AlertTriangle size={18} />
                <span>{error}</span>
              </div>
            )}
          </form>

          <div className="mt-10 text-center text-text-muted font-medium text-[13px]">
            Everfresh Poultry Pvt. Ltd. · Kathmandu
          </div>
        </div>
      </div>
    </div>
  );
}
