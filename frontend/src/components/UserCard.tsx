/**
 * 心犀AI - 用户卡片组件（v3 暗色磨砂风格）
 * ============================================
 *
 * 学习要点 — 磨砂玻璃效果:
 * .glass-card 使用 backdrop-filter: blur(12px)
 * 让卡片背后的内容模糊，产生磨砂玻璃质感。
 * 这需要父元素（body）有可见背景色，否则无效果。
 *
 * 学习要点 — framer-motion:
 * motion.div 是 framer-motion 的动画容器。
 * - whileHover: 鼠标悬停时的动画状态
 * - transition: 动画时长和缓动函数
 * - 性能：framer-motion 使用 CSS transform，在 GPU 上执行，不会触发回流
 *
 * 学习要点 — 图片加载策略:
 * 优先显示 photos[0]（用户上传的照片），
 * 如果没有则显示头像，如果都没有则显示首字母占位符。
 * 这样新用户也有好的视觉体验。
 */
import { motion } from 'framer-motion'
import { MapPin, GraduationCap, Heart } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { UserPublic } from '@/types'
import { cn } from '@/lib/utils'

interface UserCardProps {
  user: UserPublic
  className?: string
}

export default function UserCard({ user, className }: UserCardProps) {
  const navigate = useNavigate()
  // 优先用第一张照片，其次用头像作为封面
  const coverImage = user.photos?.[0] || user.avatar_url

  return (
    <motion.div
      className={cn("glass-card cursor-pointer overflow-hidden group", className)}
      whileHover={{ scale: 1.02, y: -2 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      onClick={() => navigate(`/user/${user.user_id}`)}
    >
      {/* 封面图 — 3:4 比例，适合人像 */}
      <div className="relative aspect-[3/4] bg-muted overflow-hidden">
        {coverImage ? (
          <img
            src={coverImage}
            alt={user.nickname}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          // 无图片时显示首字母占位符
          <div className="w-full h-full flex items-center justify-center">
            <div
              className="text-5xl font-bold"
              style={{
                background: 'linear-gradient(135deg, rgba(233,30,140,0.3) 0%, rgba(156,39,176,0.3) 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              {user.nickname.charAt(0)}
            </div>
          </div>
        )}

        {/* 底部渐变遮罩（让文字在任何图片上都清晰可读） */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-transparent to-transparent" />

        {/* 覆盖在图片上的信息 */}
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <div className="flex items-end justify-between">
            <div>
              <p className="font-semibold text-white text-sm leading-tight">
                {user.nickname}，{user.age}
              </p>
              <div className="flex items-center gap-1 mt-0.5">
                <MapPin size={10} className="text-white/70 flex-shrink-0" />
                <span className="text-white/70 text-[11px] truncate">{user.city}</span>
              </div>
            </div>
            <Heart
              size={16}
              className="text-white/50 group-hover:text-primary transition-colors flex-shrink-0"
            />
          </div>
        </div>
      </div>

      {/* 底部标签区 */}
      <div className="p-2 flex gap-1.5 flex-wrap">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[11px]">
          <GraduationCap size={10} />
          {user.education}
        </span>
        {user.mbti && user.mbti !== '未知' && (
          <span className="px-2 py-0.5 rounded-full bg-secondary/10 text-secondary text-[11px]">
            {user.mbti}
          </span>
        )}
      </div>
    </motion.div>
  )
}
