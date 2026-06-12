/**
 * 心犀AI - 加载状态组件
 * =======================
 *
 * 【学习要点】
 * 用 shadcn/ui 的 Skeleton 组件替代之前的"心跳 emoji + 文字"加载态。
 *
 * 骨架屏（Skeleton）vs 加载旋转器（Spinner）：
 * - Spinner：告诉用户"在加载"，但不告诉用户"加载后长什么样"
 * - Skeleton：用灰色色块预渲染布局轮廓，用户知道内容即将出现在哪
 * - 现代 UI 趋势更偏好 Skeleton，体验更好
 *
 * 提供两种模式：
 * - grid：首页的用户卡片网格加载态（显示多个卡片骨架）
 * - page：详情页的单页加载态（显示一个页面骨架）
 */
import { Skeleton } from "@/components/ui/skeleton"

interface LoadingStateProps {
  /** 加载模式 */
  variant?: 'grid' | 'page'
  /** 网格模式下显示的骨架卡片数量 */
  count?: number
}

export function LoadingState({ variant = 'page', count = 8 }: LoadingStateProps) {
  if (variant === 'grid') {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="bg-white rounded-2xl overflow-hidden shadow-sm border border-rose-100/50">
            {/* 渐变色头部骨架 */}
            <Skeleton className="h-24 w-full rounded-none" />
            {/* 头像骨架 */}
            <div className="flex justify-center -mt-8">
              <Skeleton className="h-16 w-16 rounded-full border-4 border-white" />
            </div>
            {/* 内容骨架 */}
            <div className="p-5 space-y-3">
              <Skeleton className="h-5 w-24 mx-auto" />
              <Skeleton className="h-4 w-32 mx-auto" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-3/4" />
              <div className="flex gap-1.5 justify-center pt-2">
                <Skeleton className="h-5 w-12 rounded-full" />
                <Skeleton className="h-5 w-10 rounded-full" />
                <Skeleton className="h-5 w-14 rounded-full" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  // page 模式 — 详情页骨架
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* 头部卡片骨架 */}
      <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-rose-100/50">
        <Skeleton className="h-32 w-full rounded-none" />
        <div className="p-8 space-y-4">
          <div className="flex items-center gap-4">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-10 w-32 rounded-full ml-auto" />
          </div>
          <Skeleton className="h-4 w-48" />
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
          </div>
        </div>
      </div>
    </div>
  )
}
