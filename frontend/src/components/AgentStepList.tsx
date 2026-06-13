/**
 * AgentStepList - Agent 执行步骤可视化组件
 * ==========================================
 * 将 SSE 事件流渲染为带动画的进度步骤列表。
 */

import { motion, AnimatePresence } from 'framer-motion'
import type { SSEEvent } from '@/types'

// 节点名到友好标签的映射
const NODE_LABELS: Record<string, string> = {
  intent_agent:     '🔍 意图解析',
  retrieval_agent:  '📋 候选人检索',
  hitl_node:        '👀 预览候选人',
  analysis_agent:   '🧠 深度匹配分析',
  reflection_agent: '🔄 策略优化',
  letter_agent:     '💌 生成推荐词',
  judge_agent:      '⚖️ 质量评估',
  start:            '✨ 启动',
  resume:           '🚀 继续分析',
}

// 把 SSE 事件流转换为可展示的步骤
function eventsToSteps(events: SSEEvent[]): { key: string; label: string; msg: string; done: boolean }[] {
  const steps: Map<string, { label: string; msg: string; done: boolean }> = new Map()

  for (const ev of events) {
    const node = ev.node ?? '_unknown'
    const label = NODE_LABELS[node] ?? ev.emoji ? `${ev.emoji} ${node}` : node

    if (ev.event === 'agent_start') {
      steps.set(node, { label, msg: ev.msg ?? '', done: false })
    } else if (ev.event === 'agent_complete') {
      const existing = steps.get(node)
      steps.set(node, {
        label: existing?.label ?? label,
        msg: ev.msg ?? existing?.msg ?? '',
        done: true,
      })
    } else if (ev.event === 'tool_call') {
      const existing = steps.get(node)
      if (existing) {
        existing.msg = `${existing.msg} → 调用工具: ${ev.tool}`
      }
    } else if (ev.event === 'complete') {
      steps.set('_complete', {
        label: '✅ 匹配完成',
        msg: `找到 ${ev.result_count ?? 0} 位缘分候选人`,
        done: true,
      })
    } else if (ev.event === 'error') {
      steps.set('_error', {
        label: '❌ 出错了',
        msg: ev.msg ?? '发生了未知错误',
        done: true,
      })
    }
  }

  return Array.from(steps.entries()).map(([key, val]) => ({ key, ...val }))
}

interface AgentStepListProps {
  events: SSEEvent[]
}

export default function AgentStepList({ events }: AgentStepListProps) {
  const steps = eventsToSteps(events)

  if (steps.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-gray-400 text-sm">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="ml-3">正在连接 AI 引擎...</span>
      </div>
    )
  }

  return (
    <ul className="space-y-2 py-2">
      <AnimatePresence initial={false}>
        {steps.map((step) => (
          <motion.li
            key={step.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex items-start gap-3 text-sm"
          >
            {/* 状态图标 */}
            <div className="mt-0.5 flex-shrink-0">
              {step.done ? (
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-rose-500 text-white text-[10px] font-bold">
                  ✓
                </span>
              ) : (
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full border-2 border-rose-400">
                  <span className="w-2 h-2 bg-rose-400 rounded-full animate-ping" />
                </span>
              )}
            </div>

            {/* 内容 */}
            <div className="flex-1 min-w-0">
              <p className={`font-medium leading-snug ${step.done ? 'text-gray-800' : 'text-rose-600'}`}>
                {step.label}
              </p>
              {step.msg && (
                <p className="text-gray-500 text-xs mt-0.5 leading-relaxed line-clamp-2">
                  {step.msg}
                </p>
              )}
            </div>
          </motion.li>
        ))}
      </AnimatePresence>
    </ul>
  )
}
