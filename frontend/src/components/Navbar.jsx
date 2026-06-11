/**
 * 心犀AI - 导航栏组件
 * 顶部固定导航，包含 Logo 和各页面入口。
 * 使用 react-router-dom 的 NavLink 实现路由高亮。
 */
import { NavLink } from 'react-router-dom'

export default function Navbar() {
  // NavLink 的 className 可以接收函数，根据是否激活返回不同样式
  const linkClass = ({ isActive }) =>
    `px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
      isActive
        ? 'bg-rose-500 text-white shadow-md shadow-rose-200'
        : 'text-gray-600 hover:text-rose-500 hover:bg-rose-50'
    }`

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-rose-100">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-2 no-underline">
          <span className="text-2xl animate-heartbeat inline-block">💕</span>
          <span className="text-xl font-bold bg-gradient-to-r from-rose-500 to-pink-500 bg-clip-text text-transparent">
            心犀AI
          </span>
        </NavLink>

        {/* 导航链接 */}
        <div className="flex items-center gap-2">
          <NavLink to="/" end className={linkClass}>
            🏠 发现
          </NavLink>
          <NavLink to="/create" className={linkClass}>
            ✨ 注册
          </NavLink>
          <NavLink to="/history" className={linkClass}>
            📋 历史
          </NavLink>
        </div>
      </div>
    </nav>
  )
}
