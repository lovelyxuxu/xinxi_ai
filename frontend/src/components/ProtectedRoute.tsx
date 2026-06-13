/**
 * 心犀AI - 路由守卫组件（ProtectedRoute）
 * ===========================================
 *
 * 【学习要点 — 路由守卫模式】
 * 路由守卫（Route Guard）是一种访问控制模式：
 * - requireAuth=true: 只有登录用户才能访问
 * - requireProfileComplete=true: 还需要完善过资料（profile_complete=true）
 *
 * 权限层级（低→高）：
 * 游客 → 登录用户 → 完善资料的用户
 *
 * 使用示例：
 *   // 需要登录
 *   <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
 *
 *   // 需要完善资料（缘分分析功能）
 *   <Route path="/fate/*" element={
 *     <ProtectedRoute requireProfileComplete><FatePage /></ProtectedRoute>
 *   } />
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  /** 是否需要登录（默认 true） */
  requireAuth?: boolean
  /** 是否需要完善资料（默认 false） */
  requireProfileComplete?: boolean
  /** 重定向目标（默认 /login） */
  redirectTo?: string
}

export default function ProtectedRoute({
  children,
  requireAuth = true,
  requireProfileComplete = false,
  redirectTo = '/login',
}: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  // 正在加载认证状态时显示占位
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div
          className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
          style={{ borderColor: 'rgba(102,126,234,0.6)', borderTopColor: 'transparent' }}
        />
      </div>
    )
  }

  // 1. 需要登录但未登录 → 跳到登录页，记住来源
  if (requireAuth && !isAuthenticated) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />
  }

  // 2. 需要完善资料但未完善 → 跳到编辑页，携带提示参数
  if (requireProfileComplete && user && !user.profile_complete) {
    return <Navigate to="/profile/edit?hint=complete_required" replace />
  }

  return <>{children}</>
}
