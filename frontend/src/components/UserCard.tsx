/**
 * 心犀AI - 用户卡片组件（shadcn/ui 版）
 * =========================================
 *
 * 【学习要点 — shadcn/ui Card 组件结构】
 * Card 组件由多个子组件组成，每个负责一个区域：
 * - <Card>           — 最外层容器（白色背景 + 圆角 + 阴影 + 边框）
 * - <CardHeader>     — 头部区域（标题、描述）
 * - <CardContent>    — 内容区域（主体信息）
 * - <CardFooter>     — 底部区域（操作按钮）
 *
 * 这里我们没有用 CardHeader 的传统结构，
 * 而是把渐变头部作为 Card 的自定义 children 来实现。
 * shadcn/ui 的灵活性就在于：你可以自由组合子组件。
 *
 * 【新增特性】
 * - 使用 UserAvatar 共享组件替代手写头像
 * - 使用 Badge 组件替代手写标签
 * - 动画延迟用 style={{ animationDelay }} 实现交错效果
 */
import { Link } from 'react-router-dom'
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { UserAvatar } from "@/components/UserAvatar"
import { cn } from "@/lib/utils"
import type { UserProfile } from "@/types"

interface UserCardProps {
  user: UserProfile
}

export default function UserCard({ user }: UserCardProps) {
  // 根据性别选不同的渐变色
  const genderGradient = user.gender === 'female'
    ? 'from-pink-400 to-rose-400'
    : 'from-blue-400 to-indigo-400'

  const genderEmoji = user.gender === 'female' ? '♀' : '♂'

  return (
    <Link
      to={`/user/${user.user_id}`}
      className="block no-underline animate-fade-in-up"
    >
      <Card className="overflow-hidden card-hover border-border/50 h-full">
        {/* 顶部渐变色块 */}
        <div className={cn("h-24 bg-gradient-to-br relative", genderGradient)}>
          {/* 头像 — 居中悬浮在渐变色块底部 */}
          <div className="absolute -bottom-8 left-1/2 -translate-x-1/2">
            <UserAvatar
              nickname={user.nickname}
              gender={user.gender}
              size="md"
              className="border-4 border-white"
            />
          </div>
        </div>

        {/* 用户信息 */}
        <CardContent className="pt-10 pb-5 px-5 text-center">
          <h3 className="text-lg font-bold text-gray-800 mb-1">
            {user.nickname}
            <span className={cn("ml-2 text-sm", user.gender === 'female' ? 'text-pink-400' : 'text-blue-400')}>
              {genderEmoji}
            </span>
          </h3>
          <p className="text-sm text-muted-foreground mb-3">
            {user.age}岁 · {user.city} · {user.education}
          </p>
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed px-2">
            {user.about_me}
          </p>

          {/* 兴趣标签 — 使用 shadcn Badge */}
          {user.hobbies && (
            <div className="flex flex-wrap justify-center gap-1.5 mt-3">
              {user.hobbies.split(',').slice(0, 4).map((hobby, i) => (
                <Badge
                  key={i}
                  variant="secondary"
                  className="text-xs font-normal bg-rose-50 text-rose-400 hover:bg-rose-100"
                >
                  {hobby.trim()}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}
