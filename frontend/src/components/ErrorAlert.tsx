/**
 * 心犀AI - 错误提示组件
 * ======================
 *
 * 使用 shadcn/ui 的 Alert 组件统一展示错误信息。
 *
 * 【学习要点】
 * 统一的错误展示好处：
 * 1. 所有页面的错误提示看起来一样（一致性）
 * 2. 修改样式只需改一个地方（可维护性）
 * 3. 可以方便地添加重试按钮、错误码等高级功能
 */
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

interface ErrorAlertProps {
  /** 错误信息 */
  message: string
  /** 可选的辅助说明 */
  hint?: string
  /** 可选的标题 */
  title?: string
}

export function ErrorAlert({ message, hint, title = "出错了" }: ErrorAlertProps) {
  return (
    <Alert variant="destructive" className="max-w-lg mx-auto">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <p>{message}</p>
        {hint && <p className="text-sm mt-1 opacity-80">{hint}</p>}
      </AlertDescription>
    </Alert>
  )
}
