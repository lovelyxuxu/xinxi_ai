/**
 * 心犀AI - 匹配进度面板组件
 * ============================
 *
 * 【学习要点】
 * 这是最复杂的共享组件——展示 WebSocket 实时匹配进度。
 *
 * 组件职责：
 * 1. 显示整体进度条（根据当前节点映射百分比）
 * 2. 实时展示每个 Agent 节点的执行状态
 * 3. 提供视觉反馈：执行中（脉冲动画）、完成（✓）、出错（红色）
 *
 * 数据流：
 * 父组件（UserDetail）管理 WebSocket 连接和状态，
 * 通过 props 把 wsLogs 和 currentNode 传给这个组件。
 * 这是 React 的"单向数据流"模式：数据从父到子，事件从子到父。
 */
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import type { WsLogEntry } from "@/types"

interface MatchProgressPanelProps {
  /** 当前正在执行的节点名 */
  currentNode: string
  /** 实时日志列表 */
  logs: WsLogEntry[]
}

/**
 * 节点名 → 进度百分比映射
 *
 * 【学习要点】
 * Record<string, number> 是 TypeScript 中定义"字典"的方式。
 * 等价于 { [key: string]: number }
 *
 * 新版 Supervisor 架构的节点名和旧版的对应关系：
 * - parse_intent → intent_agent (意图解析)
 * - hybrid_search → retrieval_agent (混合检索)
 * - post_analysis → analysis_agent (深度分析)
 * - reflection → reflection_agent (策略反思)
 * - generate_match → letter_agent (推荐信生成)
 * - 新增: supervisor (调度中心), judge_agent (质量评估)
 *
 * 两套名字都保留，确保切换架构后进度条仍然正常显示。
 */
const NODE_PROGRESS: Record<string, number> = {
  // 旧版单 Agent 图
  'parse_intent': 15,
  'hybrid_search': 35,
  'post_analysis': 55,
  'reflection': 70,
  'generate_match': 90,
  // 新版 Supervisor 多 Agent 图
  'supervisor': 5,
  'intent_agent': 15,
  'retrieval_agent': 35,
  'analysis_agent': 55,
  'reflection_agent': 70,
  'letter_agent': 90,
  'judge_agent': 95,
}

export function MatchProgressPanel({ currentNode, logs }: MatchProgressPanelProps) {
  // 根据当前节点名获取进度，未知节点默认 8%
  const progress = NODE_PROGRESS[currentNode] ?? 8

  return (
    <Card className="animate-fade-in-up border-rose-100/50">
      <CardContent className="p-6">
        {/* 标题区 */}
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl animate-heartbeat">💕</span>
          <div>
            <p className="text-gray-800 font-medium">AI 红娘正在为你寻找缘分</p>
            <p className="text-muted-foreground text-xs">通过 WebSocket 实时推送进度</p>
          </div>
        </div>

        {/* 进度条 */}
        <Progress value={progress} className="h-2 mb-4" />

        {/* 实时日志列表 */}
        <div className="space-y-2">
          {logs.map((log, i) => (
            <div
              key={i}
              className={cn(
                "flex items-start gap-2 text-sm py-1.5 px-3 rounded-lg transition-all",
                log.active && "bg-rose-50 text-rose-600",
                log.error && "bg-red-50 text-red-500",
                log.done && !log.error && !log.active && "text-gray-600",
                !log.active && !log.error && !log.done && "text-gray-500",
              )}
            >
              <span className="flex-shrink-0">{log.emoji}</span>
              <span className={log.active ? 'animate-pulse' : ''}>{log.text}</span>
              {log.active && <span className="ml-auto text-xs text-rose-400">执行中...</span>}
              {log.done && !log.error && <span className="ml-auto text-xs text-green-500">✓</span>}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
