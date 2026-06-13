/**
 * 心犀AI - 桌面端导航栏（v3 暗色版）
 * ======================================
 *
 * 【变更说明 v3】
 * - 背景：白色/80 → 磨砂玻璃暗色（bg-card/80 backdrop-blur-xl）
 * - 图标：emoji（🏠💕📋）→ Lucide 图标（语义清晰、可自定义颜色）
 * - 头像：空白落地色 → 渐变主色背景
 *
 * 【学习要点 — Lucide React】
 * lucide-react 是 shadcn/ui 推荐的图标库：
 * - 每个图标都是独立组件，按需引入（tree-shaking 友好）
 * - 支持 size、color、strokeWidth 等 props 自定义
 * - 用 SVG 实现，缩放清晰，不像 emoji 会受系统主题影响
 */
import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { getUnreadCount } from '@/api/client'
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Menu, LogOut, User, Heart, Settings,
  Compass, History, Sparkles, Bell,
} from "lucide-react"
import { cn } from "@/lib/utils"

const BASE_LINKS = [
  { to: '/', label: '发现', icon: Compass, end: true },
] as const

const AUTH_LINKS = [
  { to: '/fate', label: '心动', icon: Heart },
  { to: '/history', label: '历史', icon: History },
] as const

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()
  const [sheetOpen, setSheetOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  // 轮询未读通知数（每 30s 刷新一次）
  useEffect(() => {
    if (!isAuthenticated) { setUnreadCount(0); return }
    const fetchCount = async () => {
      try {
        const res = await getUnreadCount()
        setUnreadCount(res.data.unread_count)
      } catch { /* 忽略错误 */ }
    }
    fetchCount()
    const timer = setInterval(fetchCount, 30_000)
    return () => clearInterval(timer)
  }, [isAuthenticated])

  const navLinks = isAuthenticated
    ? [...BASE_LINKS, ...AUTH_LINKS]
    : BASE_LINKS

  const handleLogout = () => {
    logout()
    setMenuOpen(false)
    navigate('/')
  }

  return (
    <nav
      className="sticky top-0 z-50 border-b"
      style={{
        background: 'rgba(15, 12, 41, 0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderColor: 'var(--color-border)',
      }}
    >
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-2 no-underline">
          <Sparkles size={20} style={{ color: '#f093fb' }} className="animate-pulse" />
          <span className="text-xl font-bold text-gradient-primary">心犀AI</span>
        </NavLink>

        {/* 桌面端导航链接 — md 以上显示 */}
        <div className="hidden md:flex items-center gap-1">
          {navLinks.map(link => {
            const Icon = link.icon
            return (
              <NavLink key={link.to} to={link.to} end={('end' in link) ? link.end : false}>
                {({ isActive }) => (
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn(
                      "rounded-full text-sm gap-1.5",
                      isActive
                        ? "bg-primary/15 text-primary hover:bg-primary/20"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <Icon size={14} />
                    {link.label}
                  </Button>
                )}
              </NavLink>
            )
          })}
        </div>

        {/* 右侧：认证区域 */}
        <div className="hidden md:flex items-center gap-2">
          {isAuthenticated ? (
            <div className="relative flex items-center gap-2">
              {/* 通知铃铛 */}
              <button
                className="btn-ghost p-2 relative"
                style={{ borderRadius: '50%', border: 'none', background: 'transparent' }}
                title="通知"
                onClick={() => navigate('/fate')}
              >
                <Bell size={18} style={{ color: 'var(--color-text-secondary)' }} />
                {unreadCount > 0 && (
                  <span
                    className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full text-white text-[10px] font-bold flex items-center justify-center"
                    style={{ background: '#f093fb' }}
                  >
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </button>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="flex items-center gap-2 rounded-full px-3 py-1.5 transition-colors"
                style={{ background: 'rgba(255,255,255,0.06)' }}
              >
                <Avatar className="h-8 w-8 ring-1 ring-primary/30">
                  <AvatarImage src={user?.avatar_url || undefined} />
                  <AvatarFallback className="bg-gradient-primary text-white text-sm font-semibold">
                    {user?.nickname?.charAt(0) || '?'}
                  </AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium">{user?.nickname}</span>
              </button>

              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 top-full mt-2 w-48 glass-card py-1 z-50 shadow-xl shadow-black/30">
                    <button
                      onClick={() => { setMenuOpen(false); navigate('/profile') }}
                      className="w-full flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-muted/50 transition-colors"
                    >
                      <User size={14} className="text-muted-foreground" />
                      个人中心
                    </button>
                    <button
                      onClick={() => { setMenuOpen(false); navigate('/history') }}
                      className="w-full flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-muted/50 transition-colors"
                    >
                      <Heart size={14} className="text-muted-foreground" />
                      匹配历史
                    </button>
                    <button
                      onClick={() => { setMenuOpen(false); navigate('/settings') }}
                      className="w-full flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-muted/50 transition-colors"
                    >
                      <Settings size={14} className="text-muted-foreground" />
                      设置
                    </button>
                    <hr className="my-1 border-border" />
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
                    >
                      <LogOut size={14} />
                      退出登录
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <>
                <NavLink to="/login">
                <button className="btn-ghost text-sm px-4 py-2">登录</button>
              </NavLink>
              <NavLink to="/register">
                <button className="btn-primary text-sm px-4 py-2">注册</button>
              </NavLink>
            </>
          )}
        </div>

        {/* 移动端菜单 — md 以下显示 */}
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden text-muted-foreground">
              <Menu size={20} />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-64 bg-card border-border">
            <div className="flex flex-col gap-2 mt-8">
              {navLinks.map(link => {
                const Icon = link.icon
                return (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    end={('end' in link) ? link.end : false}
                    onClick={() => setSheetOpen(false)}
                  >
                    {({ isActive }) => (
                      <Button
                        variant="ghost"
                        className={cn(
                          "w-full justify-start rounded-full gap-2",
                          isActive ? "bg-primary/15 text-primary" : "text-muted-foreground"
                        )}
                      >
                        <Icon size={16} /> {link.label}
                      </Button>
                    )}
                  </NavLink>
                )
              })}

              <hr className="my-2 border-border" />

              {isAuthenticated ? (
                <>
                  <div className="px-4 py-2 text-sm text-muted-foreground">
                    已登录为 <strong className="text-foreground">{user?.nickname}</strong>
                  </div>
                  <NavLink to="/profile" onClick={() => setSheetOpen(false)}>
                    <Button variant="ghost" className="w-full justify-start rounded-full text-muted-foreground gap-2">
                      <User size={16} /> 个人中心
                    </Button>
                  </NavLink>
                  <Button
                    variant="ghost"
                    className="w-full justify-start rounded-full text-destructive gap-2"
                    onClick={() => { setSheetOpen(false); handleLogout() }}
                  >
                    <LogOut size={16} /> 退出登录
                  </Button>
                </>
              ) : (
                <>
                  <NavLink to="/login" onClick={() => setSheetOpen(false)}>
                    <Button variant="ghost" className="w-full justify-start rounded-full text-muted-foreground">
                      登录
                    </Button>
                  </NavLink>
                  <NavLink to="/register" onClick={() => setSheetOpen(false)}>
                    <Button className="w-full justify-start rounded-full bg-gradient-primary text-white border-0">
                      注册
                    </Button>
                  </NavLink>
                </>
              )}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  )
}
