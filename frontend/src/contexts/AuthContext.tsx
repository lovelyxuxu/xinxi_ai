/**
 * 心犀AI - 认证上下文（AuthContext）
 * ======================================
 *
 * 【学习要点 — React Context】
 * Context 是 React 的"跨层级数据传递"机制：
 * - 通常 props 需要从父组件一层层传递到子组件
 * - Context 允许在任何层级的组件中直接读取共享数据
 * - 适合全局状态：登录用户、主题设置、语言偏好等
 *
 * 本模块的设计：
 * 1. AuthContext — 存储当前用户和认证状态
 * 2. AuthProvider — 提供 login/register/logout 方法
 * 3. useAuth() — 自定义 Hook，任何组件都能调用来获取认证状态
 *
 * 使用方式：
 *   const { user, isAuthenticated, login, logout } = useAuth()
 *   if (isAuthenticated) { ... }
 */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { login as apiLogin, register as apiRegister, setTokens, clearTokens } from '@/api/client'
import type { AuthUser, LoginRequest, RegisterRequest } from '@/types'

// ============================================================
//  Context 类型定义
// ============================================================

interface AuthContextType {
  /** 当前登录用户（未登录时为 null） */
  user: AuthUser | null
  /** 是否已登录 */
  isAuthenticated: boolean
  /** 是否正在加载（登录/注册请求中） */
  isLoading: boolean
  /** 登录 */
  login: (data: LoginRequest) => Promise<void>
  /** 注册 */
  register: (data: RegisterRequest) => Promise<void>
  /** 登出 */
  logout: () => void
  /**
   * 更新当前用户信息（编辑资料后同步全局状态）
   *
   * 学习要点 — 乐观更新:
   * 保存资料成功后，立刻更新内存中的 user 对象，
   * 不需要重新登录，导航栏的昵称/头像会立刻刷新。
   */
  updateUser: (data: Partial<AuthUser>) => void
}

// ============================================================
//  创建 Context
// ============================================================

/**
 * 【学习要点】
 * createContext<AuthContextType | null>(null) 的含义：
 * - 默认值为 null，表示"还没有 Provider 包裹"
 * - 在 useAuth() 中检查 null，如果没有 Provider 就报错
 * - 这是一种防御性编程，防止在错误的位置使用 Hook
 */
const AuthContext = createContext<AuthContextType | null>(null)

// ============================================================
//  AuthProvider 组件
// ============================================================

/**
 * 认证状态提供者 — 包裹整个应用，提供全局认证状态。
 *
 * 【学习要点】
 * Provider 组件的使用模式：
 * <AuthProvider>
 *   <App />          ← App 及其所有子组件都能通过 useAuth() 访问认证状态
 * </AuthProvider>
 *
 * 状态管理策略：
 * - user: 存储完整的用户信息（从登录/注册响应中提取）
 * - Token 存储在 api/client.ts 的模块变量中（不存 localStorage）
 * - 这样刷新页面后用户需要重新登录（对安全有利）
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  /**
   * 登录
   *
   * 【学习要点】
   * useCallback 缓存函数引用，避免每次渲染都创建新函数。
   * 依赖数组 [] 表示这个函数不会依赖外部变量变化。
   */
  const login = useCallback(async (data: LoginRequest) => {
    setIsLoading(true)
    try {
      const res = await apiLogin(data)
      const userData = res.data

      // 存储 Token
      if (userData.access_token && userData.refresh_token) {
        setTokens(userData.access_token, userData.refresh_token)
      }

      // 存储用户信息（去掉 token 字段，保持 user 对象干净）
      setUser(userData)
    } finally {
      setIsLoading(false)
    }
  }, [])

  /**
   * 注册
   * 注册成功后自动登录（后端同时返回 Token）
   */
  const register = useCallback(async (data: RegisterRequest) => {
    setIsLoading(true)
    try {
      const res = await apiRegister(data)
      const userData = res.data

      if (userData.access_token && userData.refresh_token) {
        setTokens(userData.access_token, userData.refresh_token)
      }

      setUser(userData)
    } finally {
      setIsLoading(false)
    }
  }, [])

  /**
   * 登出 — 清除 Token 和用户信息
   */
  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  /**
   * 更新当前用户信息（编辑资料保存后调用）
   * 合并更新，只修改传入的字段，保留其余字段不变
   */
  const updateUser = useCallback((data: Partial<AuthUser>) => {
    setUser(prev => prev ? { ...prev, ...data } : null)
  }, [])

  // Context 值对象 — 传递给所有子组件
  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    updateUser,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

// ============================================================
//  useAuth Hook
// ============================================================

/**
 * 认证状态 Hook — 在任意组件中获取登录状态和操作方法。
 *
 * 使用示例：
 *   function MyComponent() {
 *     const { user, isAuthenticated, logout } = useAuth()
 *     return isAuthenticated ? <span>Hi, {user.nickname}</span> : <LoginButton />
 *   }
 *
 * 【学习要点】
 * 自定义 Hook 的命名约定：以 use 开头。
 * 这里封装了 useContext，并加上非空检查（防御性编程）。
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
