import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)
const TOKEN_KEY = 'facilityops-token'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [username, setUsername] = useState(null)
  // 'checking' while we verify a stored token is still valid (not expired,
  // user still exists) — prevents a flash of the login page for someone
  // who's already logged in, and equally prevents briefly showing the
  // dashboard for a token that's actually stale before redirecting away.
  const [status, setStatus] = useState(token ? 'checking' : 'anonymous')

  useEffect(() => {
    if (!token) {
      setStatus('anonymous')
      return
    }
    let cancelled = false
    axios.get(`${API_BASE_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        if (cancelled) return
        setUsername(r.data.username)
        setStatus('authenticated')
      })
      .catch(() => {
        if (cancelled) return
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setStatus('anonymous')
      })
    return () => { cancelled = true }
  }, [token])

  const login = useCallback(async (username, password) => {
    const r = await axios.post(`${API_BASE_URL}/auth/login`, { username, password })
    localStorage.setItem(TOKEN_KEY, r.data.access_token)
    setToken(r.data.access_token)
    setUsername(r.data.username)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUsername(null)
    setStatus('anonymous')
  }, [])

  return (
    <AuthContext.Provider value={{ token, username, status, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
