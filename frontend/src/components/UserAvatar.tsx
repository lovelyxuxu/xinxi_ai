/**
 * 心犀AI - 通用用户头像组件
 * ============================
 *
 * 【学习要点】
 * 使用 shadcn/ui 的 Avatar 组件 + Lucide 图标库。
 *
 * Avatar 组件结构：
 * <Avatar>                    — 容器，控制大小和形状
 *   <AvatarImage src="..." /> — 优先显示图片
 *   <AvatarFallback>          — 图片加载失败时显示回退内容
 *     {children}
 *   </AvatarFallback>
 * </Avatar>
 *
 * 目前我们没有用户头像图片，所以只显示昵称首字母作为 fallback。
 * 以后如果支持头像上传，只需给 AvatarImage 传 src 即可。
 *
 * 性别配色：
 * - 女性：粉色渐变 (from-pink-400 to-rose-400)
 * - 男性：蓝色渐变 (from-blue-400 to-indigo-400)
 */
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"

interface UserAvatarProps {
  /** 用户昵称（取首字母作为 fallback） */
  nickname: string
  /** 用户性别（决定背景渐变色） */
  gender: 'male' | 'female'
  /** 头像尺寸 */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  /** 可选的头像图片 URL */
  imageUrl?: string
  /** 额外的 CSS 类名 */
  className?: string
}

/**
 * 尺寸映射表
 *
 * 【学习要点】
 * 把尺寸选项映射到具体的 Tailwind 类名，
 * 这样组件的使用者只需传 size="md"，不用记具体的 w-16 h-16。
 * 这是"有限选项用映射，无限选项用 props"的设计原则。
 */
const sizeMap = {
  sm: 'w-10 h-10 text-base',
  md: 'w-16 h-16 text-2xl',
  lg: 'w-20 h-20 text-3xl',
  xl: 'w-24 h-24 text-4xl',
} as const

export function UserAvatar({ nickname, gender, size = 'md', imageUrl, className }: UserAvatarProps) {
  // 根据性别选择渐变色
  const genderGradient = gender === 'female'
    ? 'bg-gradient-to-br from-pink-400 to-rose-400'
    : 'bg-gradient-to-br from-blue-400 to-indigo-400'

  return (
    <Avatar className={cn(sizeMap[size], genderGradient, "text-white font-bold shadow-lg border-2 border-white", className)}>
      {imageUrl && <AvatarImage src={imageUrl} alt={nickname} />}
      <AvatarFallback className={cn(genderGradient, "text-white font-bold")}>
        {nickname?.charAt(0) || '?'}
      </AvatarFallback>
    </Avatar>
  )
}
