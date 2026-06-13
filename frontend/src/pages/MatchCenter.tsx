/**
 * MatchCenter - 匹配中心页面
 * ===========================
 * 提供完整的 SSE 匹配流程体验：
 *   1. 启动匹配（POST /match/start）
 *   2. 订阅 SSE 流，实时展示 Agent 进度
 *   3. HITL 中断：展示候选人预览，等待用户确认
 *   4. 用户点击"开始深度分析"（POST /match/{id}/resume）
 *   5. 继续展示 Agent 进度
 *   6. 匹配完成，展示最终结果卡片
 *
 * 状态机：
 *   idle → starting → streaming → waiting_hitl → streaming → done
 *                                                           ↘ error
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useSSE } from '@/hooks/useSSE'
import AgentStepList from '@/components/AgentStepList'
import { startMatch, resumeMatch, getMatchResult } from '@/api/client'
import type { SSECandidate } from '@/types'

// 从 localStorage 读取 JWT token
function getToken(): string {
  return localStorage.getItem('access_token') ?? ''
}

// 状态类型
type PageStatus = 'idle' | 'starting' | 'streaming' | 'waiting_hitl' | 'done' | 'error'

// 单个候选人预览卡片
function CandidatePreviewCard({ c }: { c: SSECandidate }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl bg-white/70 border border-rose-100 shadow-sm">
      {c.avatar_url ? (
        <img
          src={c.avatar_url}
          alt={c.nickname}
          className="w-12 h-12 rounded-full object-cover flex-shrink-0"
        />
      ) : (
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-rose-300 to-pink-400 flex items-center justify-center text-white text-lg font-bold flex-shrink-0">
          {c.nickname.charAt(0)}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-gray-800 truncate">{c.nickname}</p>
        <p className="text-xs text-gray-500">{c.age} 岁 · {c.city}</p>
      </div>
      {c.score > 0 && (
        <span className="text-xs font-bold text-rose-500 bg-rose-50 px-2 py-0.5 rounded-full flex-shrink-0">
          {c.score}分
        </span>
      )}
    </div>
  )
}

export default function MatchCenter() {
  const navigate = useNavigate()
  const { events, status: sseStatus, connect, disconnect, clearEvents } = useSSE()

  const [pageStatus, setPageStatus] = useState<PageStatus>('idle')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [hitlCandidates, setHitlCandidates] = useState<SSECandidate[]>([])
  const [retrievelNote, setRetrievalNote] = useState<string>('')
  const [finalResult, setFinalResult] = useState<Record<string, unknown> | null>(null)
  const [errorMsg, setErrorMsg] = useState<string>('')
  const isResuming = useRef(false)

  // 监听 SSE 事件，处理关键事件
  useEffect(() => {
    if (events.length === 0) return
    const last = events[events.length - 1]

    if (last.event === 'hitl_preview') {
      setHitlCandidates(last.candidates ?? [])
      setRetrievalNote(last.retrieval_note ?? '')
      setPageStatus('waiting_hitl')
    } else if (last.event === 'complete') {
      setPageStatus('done')
    } else if (last.event === 'error') {
      setErrorMsg(last.msg ?? '发生未知错误')
      setPageStatus('error')
    }
  }, [events])

  // 监听 SSE 连接关闭（流结束后加载最终结果）
  useEffect(() => {
    if (sseStatus === 'closed' && pageStatus === 'done' && sessionId) {
      getMatchResult(sessionId)
        .then((res) => {
          setFinalResult(res.data.result as Record<string, unknown>)
        })
        .catch(() => {
          // 结果可能还在处理中，忽略错误
        })
    }
  }, [sseStatus, pageStatus, sessionId])

  // 启动匹配
  const handleStart = useCallback(async () => {
    try {
      setPageStatus('starting')
      clearEvents()
      const res = await startMatch()
      const sid = res.data.session_id
      setSessionId(sid)
      setPageStatus('streaming')
      connect(sid, getToken())
    } catch {
      setErrorMsg('启动匹配失败，请稍后重试')
      setPageStatus('error')
    }
  }, [connect, clearEvents])

  // HITL 确认：开始深度分析
  const handleProceed = useCallback(async () => {
    if (!sessionId || isResuming.current) return
    isResuming.current = true
    try {
      await resumeMatch(sessionId, 'proceed')
      setPageStatus('streaming')
    } catch {
      setErrorMsg('恢复匹配失败，请刷新页面')
      setPageStatus('error')
    } finally {
      isResuming.current = false
    }
  }, [sessionId])

  // 重新匹配
  const handleRetry = useCallback(() => {
    disconnect()
    setSessionId(null)
    setHitlCandidates([])
    setRetrievalNote('')
    setFinalResult(null)
    setErrorMsg('')
    clearEvents()
    setPageStatus('idle')
  }, [disconnect, clearEvents])

  // 查看匹配详情（跳转到历史记录页）
  const handleViewDetails = useCallback(() => {
    navigate('/history')
  }, [navigate])

  const candidates = (finalResult?.candidates as Record<string, unknown>[] | undefined) ?? []

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-pink-50 to-purple-50 pb-24">
      {/* 页面标题 */}
      <div className="px-4 pt-12 pb-6">
        <h1 className="text-2xl font-bold text-gray-800">💞 匹配中心</h1>
        <p className="text-gray-500 text-sm mt-1">AI 为你智能寻找缘分候选人</p>
      </div>

      <div className="px-4 space-y-4">

        {/* ========== 状态：idle ========== */}
        <AnimatePresence mode="wait">
          {pageStatus === 'idle' && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-white rounded-2xl shadow-sm p-6 text-center space-y-4"
            >
              <div className="text-5xl">🔮</div>
              <h2 className="text-lg font-semibold text-gray-800">开始智能匹配</h2>
              <p className="text-sm text-gray-500 leading-relaxed">
                AI 将分析你的画像和偏好，从数据库中寻找最契合的缘分候选人，
                并通过多轮深度分析生成专属推荐词。
              </p>

              {/* 功能亮点 */}
              <div className="grid grid-cols-3 gap-3 py-2">
                {[
                  { icon: '🛠', label: 'Tool Calling', desc: '智能调取个人信息' },
                  { icon: '🔄', label: 'Agentic RAG', desc: '3轮自适应检索' },
                  { icon: '🤝', label: 'HITL', desc: '人工确认，精准推荐' },
                ].map((f) => (
                  <div key={f.label} className="bg-rose-50 rounded-xl p-3 text-center">
                    <div className="text-2xl">{f.icon}</div>
                    <p className="text-xs font-medium text-rose-700 mt-1">{f.label}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">{f.desc}</p>
                  </div>
                ))}
              </div>

              <button
                onClick={handleStart}
                className="w-full py-3 bg-gradient-to-r from-rose-500 to-pink-500 text-white font-semibold rounded-xl shadow-md hover:shadow-lg active:scale-95 transition-all"
              >
                开始智能匹配 ✨
              </button>
            </motion.div>
          )}

          {/* ========== 状态：starting ========== */}
          {pageStatus === 'starting' && (
            <motion.div
              key="starting"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="bg-white rounded-2xl shadow-sm p-6 text-center"
            >
              <div className="text-4xl animate-spin-slow">⚙️</div>
              <p className="text-gray-600 mt-3">正在启动 AI 引擎...</p>
            </motion.div>
          )}

          {/* ========== 状态：streaming（进行中）========== */}
          {(pageStatus === 'streaming') && (
            <motion.div
              key="streaming"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-white rounded-2xl shadow-sm p-5"
            >
              <h2 className="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-rose-500 rounded-full animate-pulse" />
                Agent 正在工作中...
              </h2>
              <AgentStepList events={events} />
            </motion.div>
          )}

          {/* ========== 状态：waiting_hitl（等待用户确认）========== */}
          {pageStatus === 'waiting_hitl' && (
            <motion.div
              key="hitl"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {/* 进度（已完成步骤） */}
              <div className="bg-white rounded-2xl shadow-sm p-5">
                <h2 className="text-sm font-medium text-gray-500 mb-3">已完成步骤</h2>
                <AgentStepList events={events} />
              </div>

              {/* HITL 预览卡 */}
              <div className="bg-white rounded-2xl shadow-sm p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-base font-semibold text-gray-800">
                    👀 找到 {hitlCandidates.length} 位候选人
                  </h2>
                  <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                    等待确认
                  </span>
                </div>

                {retrievelNote && (
                  <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2 mb-3">
                    💡 {retrievelNote}
                  </p>
                )}

                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {hitlCandidates.map((c) => (
                    <CandidatePreviewCard key={c.user_id} c={c} />
                  ))}
                </div>

                <div className="mt-4 space-y-2">
                  <button
                    onClick={handleProceed}
                    className="w-full py-3 bg-gradient-to-r from-rose-500 to-pink-500 text-white font-semibold rounded-xl shadow-md hover:shadow-lg active:scale-95 transition-all"
                  >
                    🧠 开始深度分析
                  </button>
                  <button
                    onClick={handleRetry}
                    className="w-full py-2.5 border border-gray-200 text-gray-600 text-sm rounded-xl hover:bg-gray-50 transition"
                  >
                    重新匹配
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* ========== 状态：done（完成）========== */}
          {pageStatus === 'done' && (
            <motion.div
              key="done"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {/* 完成进度 */}
              <div className="bg-white rounded-2xl shadow-sm p-5">
                <h2 className="text-sm font-medium text-gray-500 mb-3">匹配完成</h2>
                <AgentStepList events={events} />
              </div>

              {/* 结果摘要 */}
              {candidates.length > 0 && (
                <div className="bg-white rounded-2xl shadow-sm p-5">
                  <h2 className="text-base font-semibold text-gray-800 mb-3">
                    💞 为你找到 {candidates.length} 位缘分候选人
                  </h2>
                  <div className="space-y-2">
                    {(candidates as Array<{ user_id: string; nickname: string; age: number; city: string; score: number; reason: string }>)
                      .slice(0, 3).map((c) => (
                      <div key={c.user_id} className="flex gap-3 p-3 bg-rose-50 rounded-xl">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-rose-300 to-pink-400 flex items-center justify-center text-white font-bold flex-shrink-0">
                          {c.nickname?.charAt(0) ?? '?'}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-gray-800">{c.nickname}</span>
                            <span className="text-xs text-gray-500">{c.age}岁 · {c.city}</span>
                            <span className="ml-auto text-xs font-bold text-rose-500">{c.score}分</span>
                          </div>
                          {c.reason && (
                            <p className="text-xs text-gray-600 mt-1 line-clamp-2">{c.reason}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 操作按钮 */}
              <div className="space-y-2">
                <button
                  onClick={handleViewDetails}
                  className="w-full py-3 bg-gradient-to-r from-rose-500 to-pink-500 text-white font-semibold rounded-xl shadow-md hover:shadow-lg active:scale-95 transition-all"
                >
                  查看完整匹配结果
                </button>
                <button
                  onClick={handleRetry}
                  className="w-full py-2.5 border border-gray-200 text-gray-600 text-sm rounded-xl hover:bg-gray-50 transition"
                >
                  再次匹配
                </button>
              </div>
            </motion.div>
          )}

          {/* ========== 状态：error ========== */}
          {pageStatus === 'error' && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="bg-white rounded-2xl shadow-sm p-6 text-center space-y-4"
            >
              <div className="text-4xl">😕</div>
              <p className="text-gray-700 font-medium">{errorMsg || '匹配过程中出现错误'}</p>
              <button
                onClick={handleRetry}
                className="w-full py-3 bg-rose-500 text-white font-semibold rounded-xl hover:bg-rose-600 transition"
              >
                重试
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
