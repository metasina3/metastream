import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '../utils/api'
import { useAuth } from '../hooks/useAuth.jsx'
import Logo from '../components/Logo.jsx'
import DarkModeToggle from '../components/DarkModeToggle'

export default function Login() {
  const navigate = useNavigate()
  const [identity, setIdentity] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const res = await login(identity, password)
      if (!res.success) throw new Error(res.error)
      const role = res.user?.role
      navigate(role === 'admin' ? '/admin' : '/dashboard', { replace: true })
    } catch (err) {
      const msg = err?.response?.data?.detail
        || (err?.response?.data ? (typeof err.response.data === 'string' ? err.response.data : JSON.stringify(err.response.data)) : null)
        || err?.message
        || 'ایمیل/شماره یا رمز اشتباه است'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-primary opacity-20"></div>
      
      {/* Dark Mode Toggle - Top Right */}
      <div className="absolute top-6 left-6 z-10">
        <DarkModeToggle />
      </div>
      
      {/* Login Card */}
      <div className="card max-w-md w-full relative z-10">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Logo size="lg" showText={false} />
            <div className="flex flex-col">
              <h1 className="text-3xl font-bold text-gradient">
                MetaStream
              </h1>
              <p className="text-sm font-medium text-text-primary mt-1">
                Co-Streaming Platform
              </p>
            </div>
          </div>
          <h2 className="text-2xl font-semibold text-center text-text-primary">
            ورود
          </h2>
        </div>

        {error && (
          <div className="glass rounded-xl px-4 py-3 mb-6 border border-red-500/50 text-red-500">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2 text-text-primary">ایمیل یا شماره</label>
            <input
              type="text"
              value={identity}
              onChange={(e) => setIdentity(e.target.value)}
              className="input w-full"
              placeholder="admin@example.com یا 0912xxxxxxx"
              dir="ltr"
              required
            />
          </div>
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2 text-text-primary">رمز عبور</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input w-full"
              placeholder="••••••••"
              dir="ltr"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full relative"
          >
            <span className="relative z-10">{loading ? 'در حال ورود...' : 'ورود'}</span>
          </button>
        </form>
      </div>
    </div>
  )
}

