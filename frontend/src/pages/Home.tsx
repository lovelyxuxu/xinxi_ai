/**
 * 心犀AI - 首页：用户浏览（shadcn/ui 版）
 * ===========================================
 *
 * 【shadcn/ui 改进点】
 * - Select 组件替代原生 <select>（统一样式 + 更好的可访问性）
 * - Skeleton 骨架屏替代心跳 emoji 加载态（更专业的加载体验）
 * - Button 组件替代手写按钮
 * - LoadingState 共享组件
 *
 * 【学习要点 — shadcn/ui Select 组件】
 * shadcn 的 Select 基于 Radix UI，结构是：
 * <Select>                        — 状态管理
 *   <SelectTrigger>               — 触发器（看起来像一个 input）
 *     <SelectValue />             — 当前选中的值
 *   </SelectTrigger>
 *   <SelectContent>               — 下拉内容（portal 渲染，不受父容器 overflow 影响）
 *     <SelectItem value="x">     — 选项
 *   </SelectContent>
 * </Select>
 *
 * 和原生 <select> 的区别：
 * - 原生 select 样式不可控（每个浏览器不同）
 * - Radix Select 完全自定义，支持动画、搜索、分组等
 */
import { useState, useEffect } from 'react'
import { getUsers } from '../api/client'
import UserCard from '../components/UserCard'
import { LoadingState } from '@/components/LoadingState'
import { ErrorAlert } from '@/components/ErrorAlert'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { UserProfile } from '@/types'

export default function Home() {
  const [users, setUsers] = useState<UserProfile[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [genderFilter, setGenderFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')
  const pageSize = 12

  useEffect(() => {
    setLoading(true)
    setError(null)
    const filters: Record<string, string> = {}
    if (genderFilter) filters.gender = genderFilter
    if (cityFilter) filters.city = cityFilter

    getUsers(page, pageSize, filters)
      .then(res => {
        setUsers(res.data.users)
        setTotal(res.data.total)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [page, genderFilter, cityFilter])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div>
      {/* 页面标题 */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          💕 发现有缘人
        </h1>
        <p className="text-muted-foreground">
          浏览 {total} 位用户，找到你的心灵契合
        </p>
      </div>

      {/* 筛选栏 — 使用 shadcn Select */}
      <div className="flex flex-wrap justify-center gap-3 mb-8">
        <Select value={genderFilter} onValueChange={(v) => { setGenderFilter(v === 'all' ? '' : v); setPage(1) }}>
          <SelectTrigger className="w-36 rounded-full">
            <SelectValue placeholder="全部性别" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部性别</SelectItem>
            <SelectItem value="female">♀ 女生</SelectItem>
            <SelectItem value="male">♂ 男生</SelectItem>
          </SelectContent>
        </Select>

        <Select value={cityFilter} onValueChange={(v) => { setCityFilter(v === 'all' ? '' : v); setPage(1) }}>
          <SelectTrigger className="w-36 rounded-full">
            <SelectValue placeholder="全部城市" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部城市</SelectItem>
            <SelectItem value="杭州">杭州</SelectItem>
            <SelectItem value="上海">上海</SelectItem>
            <SelectItem value="北京">北京</SelectItem>
            <SelectItem value="深圳">深圳</SelectItem>
            <SelectItem value="成都">成都</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 加载状态 — 骨架屏 */}
      {loading && <LoadingState variant="grid" count={8} />}

      {/* 错误提示 */}
      {error && (
        <ErrorAlert
          message={error}
          hint="请确保后端服务已启动 (python run.py)"
        />
      )}

      {/* 用户卡片网格 */}
      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {users.map((user, i) => (
              <div key={user.user_id} style={{ animationDelay: `${i * 0.06}s` }}>
                <UserCard user={user} />
              </div>
            ))}
          </div>

          {/* 空状态 */}
          {users.length === 0 && (
            <div className="text-center py-20 text-muted-foreground">
              暂无用户，快去注册一个吧~
            </div>
          )}

          {/* 分页 — 使用 shadcn Button */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-4 mt-10">
              <Button
                variant="outline"
                size="sm"
                className="rounded-full"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                ← 上一页
              </Button>
              <span className="text-sm text-muted-foreground">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="rounded-full"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                下一页 →
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
