import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Building2, Lock, User, AlertCircle, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function LoginPage() {
  const { login } = useAuth()
  const { show } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const redirectTo = location.state?.from?.pathname || '/executive'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(username, password)
      show(`Welcome back, ${username}.`, 'success')
      navigate(redirectTo, { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Login failed — check your username and password.'
      setError(detail)
      show(detail, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0d0f13] flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-sm"
      >
        <div className="flex flex-col items-center mb-8">
          <div className="relative grid h-14 w-14 place-items-center overflow-hidden rounded-[1.15rem] bg-[#15161a] text-white shadow-lg shadow-black/40 mb-4">
            <span className="absolute -right-1 -top-1 h-4 w-4 rounded-full bg-[#c7f36a]" />
            <Building2 size={26} strokeWidth={2.2} />
          </div>
          <h1 className="font-display text-xl font-bold tracking-tight text-white">
            Facility<span className="text-teal-400">OS</span>
          </h1>
          <p className="font-mono text-[9px] tracking-[0.18em] text-slate-500 mt-1">INFOSYS · AI OPS</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 flex flex-col gap-4">
          <div>
            <label className="font-mono text-[10px] tracking-widest text-slate-500 mb-1.5 block">USERNAME</label>
            <div className="relative">
              <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-white/[0.05] border border-white/[0.1] rounded-xl py-2.5 pl-9 pr-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-teal-400/50 focus:bg-white/[0.07] transition"
                placeholder="admin"
                required
              />
            </div>
          </div>
          <div>
            <label className="font-mono text-[10px] tracking-widest text-slate-500 mb-1.5 block">PASSWORD</label>
            <div className="relative">
              <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/[0.05] border border-white/[0.1] rounded-xl py-2.5 pl-9 pr-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-teal-400/50 focus:bg-white/[0.07] transition"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2">
              <AlertCircle size={14} className="text-rose-400 mt-0.5 shrink-0" />
              <span className="font-body text-xs text-rose-300">{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-1 flex items-center justify-center gap-2 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-60 disabled:cursor-not-allowed text-[#0d0f13] font-display text-sm font-semibold py-2.5 transition"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : null}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center font-body text-[11px] text-slate-600 mt-5">
          Demo credentials are in <span className="font-mono text-slate-500">backend/.env</span> (ADMIN_USERNAME / ADMIN_PASSWORD).
        </p>
      </motion.div>
    </div>
  )
}
