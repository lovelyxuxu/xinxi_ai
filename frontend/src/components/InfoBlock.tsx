/**
 * 心犀AI - 信息展示块组件
 * =========================
 *
 * 【学习要点】
 * 这个组件解决了 DRY（Don't Repeat Yourself）问题。
 * 之前 InfoBlock 在 UserDetail.jsx 和 Profile.jsx 中各定义了一遍，
 * 代码完全相同。提取为共享组件后：
 * 1. 只需维护一份代码
 * 2. 修改样式时所有使用处同步更新
 * 3. 新页面可以直接 import 使用
 *
 * 【shadcn/ui 用法】
 * 使用 shadcn 的 Card 组件作为容器，保持视觉一致性。
 */
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface InfoBlockProps {
  /** 标签文本，显示在顶部（如 "关于我"、"兴趣爱好"） */
  label: string
  /** 内容文本，如果为空则显示 "-" */
  text: string
  /** 可选的额外 CSS 类名 */
  className?: string
}

export function InfoBlock({ label, text, className }: InfoBlockProps) {
  return (
    <Card className={cn("bg-gray-50/50 border-none shadow-none", className)}>
      <CardContent className="p-4">
        <p className="text-xs text-primary font-medium mb-1">{label}</p>
        <p className="text-sm text-gray-700 leading-relaxed">{text || '-'}</p>
      </CardContent>
    </Card>
  )
}
