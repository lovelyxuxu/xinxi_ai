/**
 * 心犀AI - 分数展示组件
 * =======================
 *
 * 统一展示匹配分数：进度条 + 颜色编码的数字。
 *
 * 【学习要点 — 提取重复逻辑为组件】
 * 之前分数的颜色判断逻辑（>=80 玫瑰色, >=60 琥珀色, 其他灰色）
 * 在 UserDetail、MatchHistory、Profile 中各写了一遍。
 * 提取到这个组件后，逻辑只写一次，所有页面共享。
 *
 * 颜色编码心理学：
 * - 80+ 分：玫瑰红 → 表示"非常好的匹配"
 * - 60-79 分：琥珀色 → 表示"还可以的匹配"
 * - 60 以下：灰色 → 表示"匹配度不高"
 */
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"

interface ScoreDisplayProps {
  /** 分数值（0-100） */
  score: number
  /** 显示模式 */
  variant?: 'badge' | 'large' | 'progress'
  /** 额外 CSS 类名 */
  className?: string
}

/**
 * 根据分数返回对应的颜色类名
 *
 * 【学习要点】
 * 把条件样式逻辑封装成纯函数，方便测试和复用。
 * 返回字符串而不是在 JSX 中写三元表达式，代码更清晰。
 */
function getScoreColor(score: number): string {
  if (score >= 80) return 'text-rose-500'
  if (score >= 60) return 'text-amber-500'
  return 'text-gray-400'
}

function getScoreBadgeVariant(score: number): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (score >= 80) return 'default'
  if (score >= 60) return 'secondary'
  return 'outline'
}

export function ScoreDisplay({ score, variant = 'badge', className }: ScoreDisplayProps) {
  if (variant === 'badge') {
    return (
      <Badge
        variant={getScoreBadgeVariant(score)}
        className={cn("font-bold", className)}
      >
        {score}分
      </Badge>
    )
  }

  if (variant === 'large') {
    return (
      <div className={cn("text-2xl font-bold", getScoreColor(score), className)}>
        {score}<span className="text-sm">分</span>
      </div>
    )
  }

  // variant === 'progress'
  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">匹配度</span>
        <span className={cn("font-bold", getScoreColor(score))}>{score}分</span>
      </div>
      <Progress value={score} className="h-2" />
    </div>
  )
}
