/**
 * 心犀AI - 用户卡片组件（v4 INS 深靛蓝风格）
 * ============================================
 *
 * 学习要点 — 玻璃形态（Glass Morphism）:
 * .glass-card 使用 backdrop-filter: blur(16px)
 * 配合半透明背景，产生 Instagram Story 风格的磨砂玻璃质感。
 *
 * 学习要点 — framer-motion:
 * motion.div 是 framer-motion 的动画容器。
 * - whileHover: 鼠标悬停时的动画状态
 * - whileTap: 点击时缩放反馈
 * - 使用 GPU 加速的 CSS transform，不触发回流
 *
 * 学习要点 — 图片加载策略:
 * 优先显示 photos[0]（用户上传的照片），
 * 如果没有则显示头像，都没有则显示渐变占位（首字母）。
 */
import { useState } from 'react'
import { motion } from 'framer-motion'
import { MapPin, Heart, GraduationCap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { UserPublic } from '@/types'
import { cn } from '@/lib/utils'

interface UserCardProps {
  user: UserPublic
  className?: string
  /** 是否已加入心动清单（Phase 3b 接通实际数据） */
  isHearted?: boolean
  /** 心动按钮点击回调（Phase 3b 接通实际逻辑） */
  onHeartToggle?: (userId: string, currentState: boolean) => void
}

/** 心动按钮 — 右下角渐变爱心（Phase 3b 完整接通） */
function HeartButton({
  isActive,
  onClick,
}: {
  isActive: boolean
  onClick: (e: React.MouseEvent) => void
}) {
  return (
    <motion.button
      className={cn(
        'btn-heart',
        isActive ? 'heart-active' : '',
      )}
      style={
        isActive
          ? {}
          : {
              background: 'rgba(255,255,255,0.15)',
              border: '1px solid rgba(255,255,255,0.25)',
            }
      }
      whileTap={{ scale: 0.85 }}
      onClick={onClick}
      aria-label={isActive ? '取消心动' : '加入心动TA们'}
    >
      <Heart size={16} fill={isActive ? 'white' : 'none'} color="white" strokeWidth={2} />
    </motion.button>
  )
}

export default function UserCard({
  user,
  className,
  isHearted = false,
  onHeartToggle,
}: UserCardProps) {
  const navigate = useNavigate()
  const [hearted, setHearted] = useState(isHearted)

  // 优先用第一张照片，其次用头像作为封面
  const coverImage = user.photos?.[0] || user.avatar_url

  const handleHeartClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    const next = !hearted
    setHearted(next)
    onHeartToggle?.(user.user_id, hearted)
  }

  return (
    <motion.div
      className={cn('glass-card glass-card-hover cursor-pointer overflow-hidden group', className)}
      transition={{ duration: 0.15, ease: 'easeOut' }}
      onClick={() => navigate(`/user/${user.user_id}`)}
    >
      {/* 封面图 — 3:4 比例，适合人像 */}
      <div className="relative aspect-[3/4] overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #1a1040 0%, #2d1b5e 100%)' }}>
        {coverImage ? (
          <img
            src={coverImage}
            alt={user.nickname}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-108"
          />
        ) : (
          // 无图时渐变首字母占位
          <div className="w-full h-full flex items-center justify-center">
            <span
              className="text-6xl font-bold select-none"
              style={{
                background: 'linear-gradient(135deg, #667eea, #f093fb)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              {user.nickname.charAt(0)}
            </span>
          </div>
        )}

        {/* 底部渐变遮罩（让文字在任何图片上都清晰可读） */}
        <div className="absolute bottom-0 left-0 right-0 h-2/5 bg-gradient-to-t from-black/70 to-transparent" />

        {/* 覆盖在图片上的信息 */}
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <div className="flex items-end justify-between">
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-white text-sm leading-tight truncate">
                {user.nickname}{user.age ? `，${user.age}` : ''}
              </p>
              {user.city && (
                <div className="flex items-center gap-1 mt-0.5">
                  <MapPin size={10} className="flex-shrink-0" style={{ color: 'rgba(255,255,255,0.65)' }} />
                  <span className="text-[11px] truncate" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    {user.city}
                  </span>
                </div>
              )}
            </div>
            {/* 心动按钮 */}
            <HeartButton isActive={hearted} onClick={handleHeartClick} />
          </div>
        </div>

        {/* 星座徽章 — 左上角 */}
        {user.zodiac_sign && (
          <div className="absolute top-2 left-2">
            <span className="badge badge-zodiac text-[10px] py-0.5 px-2">
              ✦ {user.zodiac_sign}
            </span>
          </div>
        )}
      </div>

      {/* 底部标签区 */}
      <div className="p-2.5 flex gap-1.5 flex-wrap">
        {user.education && user.education !== '未知' && (
          <span className="badge badge-mbti text-[11px]">
            <GraduationCap size={10} />
            {user.education}
          </span>
        )}
        {user.mbti && user.mbti !== '未知' && (
          <span className="badge badge-mbti text-[11px]">
            {user.mbti}
          </span>
        )}
        {user.chinese_zodiac && (
          <span className="badge badge-zodiac text-[11px]">
            {user.chinese_zodiac}年
          </span>
        )}
      </div>
    </motion.div>
  )
}
