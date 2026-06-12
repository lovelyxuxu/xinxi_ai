/**
 * 心犀AI - 导航栏组件（shadcn/ui 版）
 * =======================================
 *
 * 【学习要点 — shadcn/ui 的 Button 变体系统】
 *
 * shadcn/ui 的 Button 组件使用 CVA（class-variance-authority）实现"变体"：
 * - variant="default"  → 主色调按钮（bg-primary text-primary-foreground）
 * - variant="ghost"    → 幽灵按钮（无背景，hover 时变灰）
 * - variant="outline"  → 描边按钮
 * - variant="destructive" → 危险按钮（红色）
 *
 * 导航链接使用 variant="ghost"，因为导航项不需要太强的视觉存在感。
 * 当前激活的导航项额外添加 bg-primary/10 背景来表示高亮。
 *
 * 【学习要点 — 响应式设计】
 * - 桌面端：水平排列所有导航链接
 * - 移动端（md 以下）：隐藏链接，显示 Sheet（侧边栏）
 * - 这是"mobile-first"响应式设计的核心思想
 */
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Menu } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * 导航链接配置
 *
 * 【学习要点】
 * 把导航配置提取为数组，用 map 渲染。好处：
 * 1. 添加/删除导航项只需改数组，不用改 JSX
 * 2. 桌面端和移动端可以复用同一份配置
 */
const NAV_LINKS = [
  { to: '/', label: '发现', emoji: '🏠', end: true },
  { to: '/create', label: '注册', emoji: '✨' },
  { to: '/history', label: '历史', emoji: '📋' },
  { to: '/profile/F002', label: '我的', emoji: '👤' },
] as const

export default function Navbar() {
  // 移动端侧边栏的开关状态
  const [sheetOpen, setSheetOpen] = useState(false)

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-border">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-2 no-underline">
          <span className="text-2xl animate-heartbeat inline-block">💕</span>
          <span className="text-xl font-bold bg-gradient-to-r from-rose-500 to-pink-500 bg-clip-text text-transparent">
            心犀AI
          </span>
        </NavLink>

        {/* 桌面端导航链接 — md 以上显示 */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(link => (
            <NavLink key={link.to} to={link.to} end={link.end}>
              {({ isActive }) => (
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "rounded-full text-sm",
                    isActive && "bg-primary/10 text-primary hover:bg-primary/20"
                  )}
                >
                  {link.emoji} {link.label}
                </Button>
              )}
            </NavLink>
          ))}
        </div>

        {/* 移动端菜单按钮 — md 以下显示 */}
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-64">
            <div className="flex flex-col gap-2 mt-8">
              {NAV_LINKS.map(link => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.end}
                  onClick={() => setSheetOpen(false)}
                >
                  {({ isActive }) => (
                    <Button
                      variant="ghost"
                      className={cn(
                        "w-full justify-start rounded-full",
                        isActive && "bg-primary/10 text-primary"
                      )}
                    >
                      {link.emoji} {link.label}
                    </Button>
                  )}
                </NavLink>
              ))}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  )
}
