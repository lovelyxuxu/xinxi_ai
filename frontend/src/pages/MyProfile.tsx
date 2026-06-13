/**
 * 心犀AI - 个人中心页面
 * =======================
 *
 * 展示内容：
 * - 头像 + 基本信息 + 编辑按钮
 * - 数据统计（匹配次数、关注数、粉丝数）
 * - 关于我 / 兴趣爱好
 * - 照片墙
 * - 快捷操作（寻找缘分、AI访谈）
 */
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Pencil, Heart, Sparkles, MapPin, GraduationCap,
  CalendarDays,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'

// 交错动画 variant
const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.25 },
  }),
}

export default function MyProfile() {
  const { user } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  const stats = [
    { label: '匹配次数', value: 0 },
    { label: '关注', value: 0 },
    { label: '粉丝', value: 0 },
  ]

  // 爱好标签
  const hobbyTags = user.hobbies
    ? user.hobbies.split(/[,，]/).map(h => h.trim()).filter(Boolean)
    : []

  return (
    <div className="max-w-lg mx-auto space-y-4 pb-24 md:pb-8">

      {/* 个人信息卡 */}
      <motion.div
        custom={0}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        className="glass-card-glow p-5"
      >
        <div className="flex items-start gap-4">
          {/* 头像 */}
          <div className="relative flex-shrink-0">
            <Avatar className="w-20 h-20 ring-2 ring-primary/30 ring-offset-2 ring-offset-background">
              <AvatarImage src={user.avatar_url || undefined} />
              <AvatarFallback className="bg-gradient-primary text-white text-2xl font-bold">
                {user.nickname.charAt(0)}
              </AvatarFallback>
            </Avatar>
          </div>

          {/* 基本信息 */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-lg font-bold">{user.nickname}</h1>
                <p className="text-xs text-muted-foreground mt-0.5">{user.user_id}</p>
              </div>
              {/* 编辑按钮 */}
              <Button
                size="icon"
                variant="ghost"
                onClick={() => navigate('/profile/edit')}
                className="text-muted-foreground hover:text-primary -mt-1 -mr-1 h-8 w-8"
              >
                <Pencil size={16} />
              </Button>
            </div>

            {/* 标签行 */}
            <div className="flex flex-wrap gap-1.5 mt-2">
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <MapPin size={11} /> {user.city}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <GraduationCap size={11} /> {user.education}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <CalendarDays size={11} /> {user.age}岁
              </span>
              {user.mbti && user.mbti !== '未知' && (
                <span className="px-2 py-0.5 rounded-full bg-secondary/15 text-secondary text-xs">
                  {user.mbti}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 关于我 */}
        {user.about_me && (
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed line-clamp-3 border-t border-border pt-3">
            {user.about_me}
          </p>
        )}
      </motion.div>

      {/* 数据统计 */}
      <motion.div
        custom={1}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        className="glass-card"
      >
        <div className="grid grid-cols-3 divide-x divide-border">
          {stats.map(({ label, value }) => (
            <div key={label} className="flex flex-col items-center py-4">
              <span className="text-2xl font-bold gradient-text">{value}</span>
              <span className="text-xs text-muted-foreground mt-1">{label}</span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* 兴趣爱好 */}
      {hobbyTags.length > 0 && (
        <motion.div
          custom={2}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="glass-card p-4 space-y-2"
        >
          <h2 className="text-sm font-medium text-muted-foreground">兴趣爱好</h2>
          <div className="flex flex-wrap gap-2">
            {hobbyTags.map(tag => (
              <span
                key={tag}
                className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        </motion.div>
      )}

      {/* 照片墙 */}
      {(user.photos?.length ?? 0) > 0 && (
        <motion.div
          custom={3}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="glass-card p-4 space-y-3"
        >
          <h2 className="text-sm font-medium text-muted-foreground">我的照片</h2>
          <div className="grid grid-cols-3 gap-2">
            {user.photos!.map((url, i) => (
              <div key={i} className="aspect-square rounded-lg overflow-hidden">
                <img
                  src={url}
                  alt={`照片${i + 1}`}
                  className="w-full h-full object-cover hover:scale-105 transition-transform cursor-pointer"
                />
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* 快捷操作 */}
      <motion.div
        custom={4}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 gap-3"
      >
        <Button
          onClick={() => navigate('/match')}
          className={cn(
            "h-14 bg-gradient-primary text-white border-0",
            "flex flex-col gap-0.5 rounded-xl font-medium",
            "shadow-lg shadow-primary/30 hover:opacity-90"
          )}
        >
          <Heart size={20} />
          <span className="text-xs">寻找缘分</span>
        </Button>
        <Button
          onClick={() => navigate('/interview')}
          variant="outline"
          className={cn(
            "h-14 border-primary/30 text-primary",
            "hover:bg-primary/10 hover:border-primary/50",
            "flex flex-col gap-0.5 rounded-xl"
          )}
        >
          <Sparkles size={20} />
          <span className="text-xs">AI 访谈</span>
        </Button>
      </motion.div>

      {/* 没有头像和照片时的引导 */}
      {!user.avatar_url && (user.photos?.length ?? 0) === 0 && (
        <motion.div
          custom={5}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="glass-card p-4 flex items-center gap-3 border-primary/20"
        >
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Pencil size={16} className="text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">完善你的资料</p>
            <p className="text-xs text-muted-foreground mt-0.5">上传头像和照片，让更多人认识你</p>
          </div>
          <Button
            size="sm"
            onClick={() => navigate('/profile/edit')}
            className="flex-shrink-0 bg-gradient-primary text-white border-0 text-xs"
          >
            去完善
          </Button>
        </motion.div>
      )}
    </div>
  )
}
