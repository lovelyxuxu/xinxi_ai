/**
 * 心犀AI - 发现页（v3 小红书风格双列瀑布流）
 * ==============================================
 *
 * 学习要点 — CSS Grid 双列布局:
 * grid-cols-2 配合 aspect-[3/4] 的 UserCard，实现均匀的双列效果。
 * staggerChildren 动画：每张卡片依次淡入，产生逐个出现的视觉效果。
 *
 * 学习要点 — 骨架屏（Skeleton）:
 * 加载时显示与真实内容形状相同的占位块，比 spinner 更好的体验。
 * animate-pulse 是 Tailwind 内置的脉冲动画。
 */
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { SlidersHorizontal, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import UserCard from '@/components/UserCard'
import { getUsers } from '@/api/client'
import type { UserPublic } from '@/types'

export default function Home() {
  const [users, setUsers] = useState<UserPublic[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [genderFilter, setGenderFilter] = useState<string>('')
  const [citySearch, setCitySearch] = useState('')
  const [loadingMore, setLoadingMore] = useState(false)

  const fetchUsers = async (p = 1, reset = false) => {
    if (p === 1) setLoading(true)
    else setLoadingMore(true)

    try {
      const params: Record<string, string | number> = {
        page: p,
        page_size: 20,
      }
      if (genderFilter) params.gender = genderFilter
      if (citySearch) params.city = citySearch

      const res = await getUsers(p, 20, {
        ...(genderFilter ? { gender: genderFilter } : {}),
        ...(citySearch ? { city: citySearch } : {}),
      })

      const data = res.data
      setTotal(data.total)
      // UserListResponse.users 现在是 UserPublic[]
      const newUsers = data.users as unknown as UserPublic[]
      setUsers(prev => reset ? newUsers : [...prev, ...newUsers])
      setPage(p)
    } catch (e) {
      console.error('加载用户列表失败', e)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  useEffect(() => {
    fetchUsers(1, true)
  }, [genderFilter])

  const handleSearch = () => fetchUsers(1, true)

  return (
    <div className="space-y-4">
      {/* 搜索和筛选栏（sticky，滚动时固定在 Navbar 下方） */}
      <div className="flex gap-2 sticky top-16 z-10 py-2 -mx-4 px-4 bg-background/90 backdrop-blur-md">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索城市..."
            value={citySearch}
            onChange={e => setCitySearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            className="pl-8 bg-card border-border h-9 text-sm placeholder:text-muted-foreground"
          />
        </div>
        {(['', 'female', 'male'] as const).map(g => (
          <Button
            key={g}
            size="sm"
            variant={genderFilter === g ? 'default' : 'outline'}
            onClick={() => setGenderFilter(g)}
            className={
              genderFilter === g
                ? "h-9 px-3 text-xs bg-gradient-primary text-white border-0"
                : "h-9 px-3 text-xs border-border text-muted-foreground hover:text-foreground"
            }
          >
            {g === '' ? '全部' : g === 'female' ? '她' : '他'}
          </Button>
        ))}
      </div>

      {/* 用户计数 */}
      {!loading && (
        <p className="text-xs text-muted-foreground px-0.5">
          共 <span className="text-primary font-medium">{total}</span> 位用户
        </p>
      )}

      {/* 双列瀑布流 */}
      {loading ? (
        // 骨架屏：8 个占位卡片
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="glass-card animate-pulse aspect-[3/4] rounded-xl"
            />
          ))}
        </div>
      ) : (
        <motion.div
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.05 } },
          }}
        >
          {users.map(user => (
            <motion.div
              key={user.user_id}
              variants={{
                hidden: { opacity: 0, y: 16 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.25 } },
              }}
            >
              <UserCard user={user} />
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* 加载更多 */}
      {!loading && users.length < total && (
        <div className="flex justify-center pt-4 pb-20 md:pb-4">
          <Button
            variant="outline"
            onClick={() => fetchUsers(page + 1)}
            disabled={loadingMore}
            className="border-border text-muted-foreground hover:text-foreground"
          >
            {loadingMore ? (
              <span className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-muted-foreground/40 border-t-muted-foreground rounded-full animate-spin" />
                加载中...
              </span>
            ) : '加载更多'}
          </Button>
        </div>
      )}

      {/* 空状态 */}
      {!loading && users.length === 0 && (
        <div className="text-center py-20 text-muted-foreground">
          <SlidersHorizontal size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">暂时没有找到符合条件的用户</p>
        </div>
      )}
    </div>
  )
}
