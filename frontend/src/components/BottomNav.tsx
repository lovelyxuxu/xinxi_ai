/**
 * 心犀AI - 移动端底部导航栏
 * ============================
 *
 * 学习要点 — 移动端专属导航:
 * - md:hidden — 在 ≥768px 宽度时隐藏（桌面端不显示）
 * - fixed bottom-0 — 固定在屏幕底部，不随页面滚动
 * - 中间 AI 访谈按钮凸起（-mt-5），突出核心功能入口
 * - pb-safe — 适配 iPhone 的 Home 指示条（env(safe-area-inset-bottom)）
 *
 * 学习要点 — NavLink 的 isActive:
 * NavLink 自动检测当前路由，通过渲染函数传递 isActive 状态。
 * 这样不需要手动比较路径，直接用 isActive 切换激活样式。
 */
import { NavLink, useLocation } from 'react-router-dom'
import { Compass, Heart, Sparkles, MessageCircle, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { useAppStore } from '@/stores/appStore'

export default function BottomNav() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  const unreadCount = useAppStore((s) => s.unreadCount)

  // 登录页和注册页不显示底部导航
  const hideOn = ['/login', '/register']
  if (hideOn.includes(location.pathname)) return null

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-card/90 backdrop-blur-xl border-t border-border pb-safe">
      <div className="flex items-center justify-around h-16 px-2">

        {/* 发现 */}
        <NavLink to="/" end className="flex-1">
          {({ isActive }) => (
            <NavItem icon={<Compass size={22} />} label="发现" isActive={isActive} />
          )}
        </NavLink>

        {/* 心动清单 */}
        <NavLink to="/fate" className="flex-1">
          {({ isActive }) => (
            <NavItem icon={<Heart size={22} />} label="心动" isActive={isActive} />
          )}
        </NavLink>

        {/* 匹配中心（Phase 3c） */}
        <NavLink to="/match" className="flex-1">
          {({ isActive }) => (
            <NavItem icon={<Sparkles size={22} />} label="匹配" isActive={isActive} />
          )}
        </NavLink>

        {/* AI 访谈 — 凸起的中心按钮（核心功能入口） */}
        <NavLink to="/interview" className="flex-1 flex justify-center -mt-5">
          <div
            className={cn(
              "flex flex-col items-center justify-center",
              "w-14 h-14 rounded-full",
              "bg-gradient-primary shadow-lg",
              "shadow-[0_4px_20px_rgba(233,30,140,0.5)]",
              "transition-transform active:scale-90"
            )}
          >
            <Sparkles size={24} className="text-white" />
          </div>
        </NavLink>

        {/* 消息 */}
        <NavLink to="/chat" className="flex-1">
          {({ isActive }) => (
            <NavItem
              icon={
                <div className="relative">
                  <MessageCircle size={22} />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-accent text-white text-[10px] font-bold flex items-center justify-center">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </div>
              }
              label="消息"
              isActive={isActive}
            />
          )}
        </NavLink>

        {/* 我的 */}
        <NavLink to={isAuthenticated ? '/profile' : '/login'} className="flex-1">
          {({ isActive }) => (
            <NavItem icon={<User size={22} />} label="我的" isActive={isActive} />
          )}
        </NavLink>

      </div>
    </nav>
  )
}

function NavItem({
  icon,
  label,
  isActive,
}: {
  icon: React.ReactNode
  label: string
  isActive: boolean
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-0.5 py-1 transition-colors",
        isActive ? "text-primary" : "text-muted-foreground"
      )}
    >
      {icon}
      <span className="text-[10px] font-medium">{label}</span>
    </div>
  )
}
