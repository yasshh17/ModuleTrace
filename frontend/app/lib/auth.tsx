'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'

import { getMe, login as apiLogin } from './api'
import type { Role, UserResponse } from './types'

const TOKEN_KEY = 'mt_token'
const COOKIE_MAX_AGE = 60 * 60 * 8 // 8 hours

interface AuthContextValue {
  user: UserResponse | null
  loading: boolean
  login: (email: string, password: string) => Promise<Role>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function setTokenCookie(token: string): void {
  document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`
}

function clearTokenCookie(): void {
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [loading, setLoading] = useState(true)

  // Hydrate user from stored token on mount
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => {
        // Token is expired or invalid — clean up
        localStorage.removeItem(TOKEN_KEY)
        clearTokenCookie()
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(
    async (email: string, password: string): Promise<Role> => {
      const { access_token, role } = await apiLogin(email, password)
      localStorage.setItem(TOKEN_KEY, access_token)
      setTokenCookie(access_token)
      const me = await getMe()
      setUser(me)
      return role
    },
    [],
  )

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    clearTokenCookie()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return ctx
}
