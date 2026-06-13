/**
 * 心犀AI - 路由守卫组件（ProtectedRoute）
 * ===========================================
 *
 * 【学习要点 — 路由守卫模式】
 * 路由守卫（Route Guard）是一种访问控制模式：
 * - 某些页面只有登录用户才能访问（如个人中心、匹配历史）
 * - 未登录用户访问这些页面时，自动重定向到登录页
 * - 类似于后端的 get_current_user 依赖注入，但这是前端版本
 *
 * 实现原理：
 * - 用 useAuth() 检查认证状态
 * - 已登录 → 渲染子组件（children）
 * - 未登录 → <Navigate> 重定向到 /login
 *
 * 使用方式：
 *   <Route path="/history" element={
 *     <ProtectedRoute><MatchHistory /></ProtectedRoute>
 *   } />
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  // 未登录 → 重定向到登录页，并记住来源页面
  if (!isAuthenticated) {
    // 【学习要点】
    // state={{ from: location }} 把当前 URL 传递给登录页
    // 登录成功后可以跳回原来的页面，用户体验更好
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // 已登录 → 正常渲染子组件
  return <>{children}</>
}
