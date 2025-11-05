import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '../utils/api'
import { useAuth } from '../hooks/useAuth.jsx'

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-500 to-primary-700">
      <div className="card max-w-md w-full">
        <div className="flex flex-col items-center mb-6">
          <img 
            src="/logo.png" 
            alt="Meta Stream Logo" 
            className="w-16 h-16 object-contain mb-3 flex-shrink-0"
            loading="eager"
            onError={(e) => {
              e.target.style.display = 'none'
            }}
          />
          <h2 className="text-2xl font-bold text-center text-primary-600">
            ورود به Meta Stream
          </h2>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">ایمیل یا شماره</label>
            <input
              type="text"
              value={identity}
              onChange={(e) => setIdentity(e.target.value)}
              className="input w-full"
              placeholder="admin@example.com یا 0912xxxxxxx"
              required
            />
          </div>
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">رمز عبور</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input w-full"
              placeholder="••••••••"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full"
          >
            {loading ? 'در حال ورود...' : 'ورود'}
          </button>
        </form>
      </div>
    </div>
  )
}

