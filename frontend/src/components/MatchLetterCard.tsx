/**
 * 心犀AI - 推荐信卡片组件
 * =========================
 *
 * 展示 AI 红娘为匹配用户生成的缘分推荐信。
 * 使用渐变背景和优雅的排版，让推荐信看起来更浪漫。
 */
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface MatchLetterCardProps {
  /** 推荐信正文 */
  letter: string
  /** 候选人昵称（显示在标题中） */
  candidateName?: string
  /** 信件编号（从 0 开始） */
  index?: number
}

export function MatchLetterCard({ letter, candidateName }: MatchLetterCardProps) {
  return (
    <Card className="border-rose-200/50 bg-gradient-to-br from-rose-50 to-pink-50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-rose-600">
          <span>💌</span>
          缘分推荐信 {candidateName && `- ${candidateName}`}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{letter}</p>
      </CardContent>
    </Card>
  )
}
