/**
 * 缘分分析结果页（FateAnalysis）
 * 支持4种分析类型：group_overview / deep_compatibility / comm_advice / comparison
 * 使用轮询等待 Agent 完成后渲染结果
 */
import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles, Star, Heart, MessageSquare, BarChart3,
  ArrowRight, RefreshCcw, ChevronDown, Trophy
} from 'lucide-react'
import { getFateAnalysis, createFateAnalysis } from '@/api/client'
import type { FateAnalysisRecord, MatchParams } from '@/types'
import FateParamsDrawer from '@/components/FateParamsDrawer'

// 类型工具：从 unknown 安全转为基础类型
const s = (v: unknown): string => (typeof v === 'string' ? v : String(v ?? ''))
const n = (v: unknown): number => (typeof v === 'number' ? v : Number(v ?? 0))
const arr = (v: unknown): string[] => (Array.isArray(v) ? (v as string[]) : [])

// ── 分数圆环 ────────────────────────────────────────────────
function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const r = (size - 8) / 2
  const circumference = 2 * Math.PI * r
  const offset = circumference - (score / 100) * circumference
  const color = score >= 85 ? '#f093fb' : score >= 70 ? '#667eea' : '#4ade80'
  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={6} />
      <motion.circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth={6} strokeLinecap="round"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.2, ease: 'easeOut' }}
      />
    </svg>
  )
}

// ── 候选者结果卡片 ────────────────────────────────────────────
function CandidateResultCard({
  c, isTop, onUpgrade
}: {
  c: Record<string, unknown>
  isTop: boolean
  onUpgrade: (candidateId: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const score = n(c.overall_score)
  const color = (typeof c.energy_color === 'string' && c.energy_color) ? c.energy_color : '#667eea'

  return (
    <motion.div layout className="glass-card overflow-hidden"
      style={isTop ? { border: '1px solid rgba(240,147,251,0.4)' } : {}}>
      <div className="h-1.5" style={{ background: `linear-gradient(90deg, ${color}, #f093fb)` }} />
      <div className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            {isTop && (
              <div className="flex items-center gap-1 mb-1">
                <Trophy size={12} style={{ color: '#fbbf24' }} />
                <span className="text-xs font-medium" style={{ color: '#fbbf24' }}>最推荐</span>
              </div>
            )}
            <h3 className="font-bold text-lg" style={{ color: 'var(--color-text)' }}>{s(c.candidate_name)}</h3>
            <p className="text-sm mt-0.5" style={{ color }}>{s(c.headline)}</p>
          </div>
          <div className="relative flex items-center justify-center w-16 h-16">
            <ScoreRing score={score} size={64} />
            <span className="absolute text-lg font-bold" style={{ color }}>{score}</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {[
            { label: '星座', note: s(c.zodiac_note) },
            { label: '属相', note: s(c.chinese_zodiac_note) },
            { label: 'MBTI', note: s(c.mbti_note) },
          ].filter(({ note }) => note).map(({ label, note }) => (
            <div key={label} className="rounded-xl p-2 text-center" style={{ background: 'rgba(255,255,255,0.04)' }}>
              <div className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>{label}</div>
              <div className="text-xs leading-relaxed" style={{ color: 'var(--color-text)' }}>{note}</div>
            </div>
          ))}
        </div>

        {c.tarot_card ? (
          <div className="flex items-center gap-2 p-3 rounded-xl" style={{ background: 'rgba(102,126,234,0.1)' }}>
            <span className="text-2xl">{s(c.tarot_emoji)}</span>
            <div>
              <div className="text-sm font-medium" style={{ color: '#a5b4fc' }}>缘分牌：{s(c.tarot_card)}</div>
              <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{s(c.tarot_reading)}</div>
            </div>
          </div>
        ) : null}

        {arr(c.pros).length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {arr(c.pros).map((pro, i) => (
              <span key={i} className="text-xs px-2.5 py-1 rounded-full"
                style={{ background: 'rgba(240,147,251,0.1)', color: '#f093fb', border: '1px solid rgba(240,147,251,0.2)' }}>
                ✦ {pro}
              </span>
            ))}
          </div>
        ) : null}

        <button onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between py-1 text-sm"
          style={{ color: 'var(--color-text-secondary)' }}>
          <span>综合小结</span>
          <ChevronDown size={14} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </button>
        <AnimatePresence>
          {expanded ? (
            <motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="text-sm leading-relaxed overflow-hidden"
              style={{ color: 'var(--color-text-secondary)' }}>
              {s(c.summary)}
            </motion.p>
          ) : null}
        </AnimatePresence>

        <button onClick={() => onUpgrade(s(c.candidate_id))}
          className="w-full btn-ghost text-sm py-2 flex items-center justify-center gap-2 border"
          style={{ borderColor: 'rgba(240,147,251,0.3)', color: '#f093fb' }}>
          <Sparkles size={14} />缘分升级分析<ArrowRight size={14} />
        </button>
      </div>
    </motion.div>
  )
}

// ── 升级分析选择器 ────────────────────────────────────────────
function UpgradeSelector({
  candidateId, onSelect, onCancel
}: {
  candidateId: string
  onSelect: (type: string, id: string) => void
  onCancel: () => void
}) {
  const options = [
    { type: 'deep_compatibility', label: '深度相性分析', icon: Heart, desc: '爱情语言·价值观·摩擦点' },
    { type: 'comm_advice', label: '沟通破冰建议', icon: MessageSquare, desc: '开场白·约会点子·话题推荐' },
    { type: 'comparison', label: '横向对比报告', icon: BarChart3, desc: '多维度评分·优劣势可视化' },
  ]
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      className="glass-card p-5 space-y-4">
      <h4 className="font-bold" style={{ color: 'var(--color-text)' }}>选择升级分析类型</h4>
      <div className="space-y-2">
        {options.map(opt => {
          const Icon = opt.icon
          return (
            <button key={opt.type} onClick={() => onSelect(opt.type, candidateId)}
              className="w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--color-border)' }}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'rgba(240,147,251,0.1)' }}>
                <Icon size={18} style={{ color: '#f093fb' }} />
              </div>
              <div>
                <div className="font-medium text-sm" style={{ color: 'var(--color-text)' }}>{opt.label}</div>
                <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{opt.desc}</div>
              </div>
              <ArrowRight size={16} className="ml-auto" style={{ color: 'var(--color-text-secondary)' }} />
            </button>
          )
        })}
      </div>
      <button onClick={onCancel} className="btn-ghost w-full text-sm">取消</button>
    </motion.div>
  )
}

// ── 主页面 ────────────────────────────────────────────────────
export default function FateAnalysis() {
  const { analysisId } = useParams<{ analysisId: string }>()
  const navigate = useNavigate()
  const [record, setRecord] = useState<FateAnalysisRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [paramsDrawerOpen, setParamsDrawerOpen] = useState(false)
  const [matchParams, setMatchParams] = useState<MatchParams>({})
  const [upgradeTarget, setUpgradeTarget] = useState<string | null>(null)
  const [launching, setLaunching] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!analysisId) return
    const poll = async () => {
      try {
        const res = await getFateAnalysis(analysisId)
        setRecord(res.data)
        if (res.data.status === 'done' || res.data.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current)
          setLoading(false)
        }
      } catch {
        setError('获取分析结果失败')
        setLoading(false)
        if (pollRef.current) clearInterval(pollRef.current)
      }
    }
    poll()
    pollRef.current = setInterval(poll, 2500)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [analysisId])

  const handleUpgrade = async (type: string, candidateId: string) => {
    setUpgradeTarget(null)
    setLaunching(true)
    try {
      const res = await createFateAnalysis({
        analysis_type: type as 'group_overview' | 'deep_compatibility' | 'comm_advice' | 'comparison',
        candidate_ids: [candidateId],
        match_params_override: Object.keys(matchParams).length > 0 ? (matchParams as Record<string, unknown>) : null,
        parent_analysis_id: analysisId,
      })
      navigate(`/fate/analysis/${res.data.analysis_id}`)
    } catch {
      setError('发起升级分析失败，请稍后重试')
    } finally {
      setLaunching(false)
    }
  }

  if (loading || (record && record.status === 'pending')) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
        <div className="relative">
          <div className="w-20 h-20 rounded-full border-4 border-transparent animate-spin"
            style={{ borderTopColor: '#f093fb', borderRightColor: '#667eea' }} />
          <div className="absolute inset-0 flex items-center justify-center">
            <Sparkles size={24} style={{ color: '#f093fb' }} className="animate-pulse" />
          </div>
        </div>
        <div className="text-center space-y-1">
          <p className="font-bold text-lg text-gradient-primary">心犀 AI 正在分析缘分...</p>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            正在计算星座、属相、MBTI 相性，请稍候
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
          <RefreshCcw size={12} className="animate-spin" />正在与 AI 沟通中...
        </div>
      </div>
    )
  }

  if (record?.status === 'failed' || error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-64 gap-4 px-4">
        <div className="text-4xl">😔</div>
        <p className="font-medium" style={{ color: 'var(--color-text)' }}>分析暂时失败</p>
        <p className="text-sm text-center" style={{ color: 'var(--color-text-secondary)' }}>
          {error || '请检查网络连接或稍后重试'}
        </p>
        <button className="btn-primary px-6" onClick={() => navigate('/fate')}>返回心动清单</button>
      </div>
    )
  }

  if (!record?.result) return null

  const result = record.result

  // ── group_overview ─────────────────────────────────────────
  const renderGroupOverview = () => {
    const candidates = Array.isArray(result.candidates) ? (result.candidates as Record<string, unknown>[]) : []
    const topId = s(result.top_recommendation)
    return (
      <div className="space-y-5">
        {result.initiator_insight ? (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <Star size={16} style={{ color: '#fbbf24' }} />
              <span className="text-sm font-medium" style={{ color: '#fbbf24' }}>红娘洞察</span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text)' }}>
              {s(result.initiator_insight)}
            </p>
          </motion.div>
        ) : null}

        {candidates.map((c, i) => (
          <motion.div key={s(c.candidate_id)} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
            <CandidateResultCard c={c} isTop={s(c.candidate_id) === topId} onUpgrade={id => setUpgradeTarget(id)} />
          </motion.div>
        ))}

        {result.recommendation_reason ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="glass-card p-4">
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              <span className="font-medium" style={{ color: '#f093fb' }}>💡 红娘推荐：</span>
              {s(result.recommendation_reason)}
            </p>
          </motion.div>
        ) : null}
      </div>
    )
  }

  // ── deep_compatibility ─────────────────────────────────────
  const renderDeepCompatibility = () => {
    const analyses = Array.isArray(result.analyses) ? (result.analyses as Record<string, unknown>[]) : []
    return (
      <div className="space-y-4">
        {analyses.map((a, i) => (
          <motion.div key={s(a.candidate_id)} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
            className="glass-card p-5 space-y-4">
            <h3 className="font-bold text-lg text-gradient-primary">{s(a.candidate_name)}</h3>

            {a.compatibility_matrix ? (
              <div className="space-y-2">
                <div className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>相性矩阵</div>
                {Object.entries(a.compatibility_matrix as Record<string, Record<string, unknown>>).map(([dim, val]) => (
                  <div key={dim} className="flex items-center gap-3">
                    <span className="text-xs w-16 flex-shrink-0" style={{ color: 'var(--color-text-secondary)' }}>{dim}</span>
                    <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.1)' }}>
                      <motion.div initial={{ width: 0 }} animate={{ width: `${n(val.score)}%` }}
                        transition={{ duration: 0.8, delay: i * 0.1 }} className="h-full rounded-full"
                        style={{ background: 'linear-gradient(90deg, #667eea, #f093fb)' }} />
                    </div>
                    <span className="text-xs w-8 text-right" style={{ color: '#f093fb' }}>{n(val.score)}</span>
                    <span className="text-xs flex-1" style={{ color: 'var(--color-text-secondary)' }}>{s(val.note)}</span>
                  </div>
                ))}
              </div>
            ) : null}

            {Array.isArray(a.friction_points) && arr(a.friction_points).length > 0 ? (
              <div>
                <div className="text-sm font-medium mb-2" style={{ color: '#fbbf24' }}>⚡ 潜在摩擦点</div>
                <div className="flex flex-wrap gap-2">
                  {arr(a.friction_points).map((fp, j) => (
                    <span key={j} className="text-xs px-2.5 py-1 rounded-full"
                      style={{ background: 'rgba(251,191,36,0.1)', color: '#fbbf24' }}>{fp}</span>
                  ))}
                </div>
              </div>
            ) : null}

            <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>{s(a.final_verdict)}</p>
          </motion.div>
        ))}
      </div>
    )
  }

  // ── comm_advice ────────────────────────────────────────────
  const renderCommAdvice = () => {
    const advices = Array.isArray(result.advices) ? (result.advices as Record<string, unknown>[]) : []
    return (
      <div className="space-y-4">
        {advices.map((a, i) => (
          <motion.div key={s(a.candidate_id)} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
            className="glass-card p-5 space-y-4">
            <h3 className="font-bold text-lg text-gradient-primary">{s(a.candidate_name)}</h3>

            {Array.isArray(a.opening_lines) ? (
              <div>
                <div className="text-sm font-medium mb-2" style={{ color: '#4ade80' }}>💬 破冰第一句</div>
                <div className="space-y-2">
                  {arr(a.opening_lines).map((line, j) => (
                    <div key={j} className="p-3 rounded-xl text-sm"
                      style={{ background: 'rgba(74,222,128,0.08)', color: 'var(--color-text)' }}>
                      "{line}"
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {Array.isArray(a.date_ideas) ? (
              <div>
                <div className="text-sm font-medium mb-2" style={{ color: '#f093fb' }}>📍 约会方案</div>
                <div className="flex flex-col gap-2">
                  {arr(a.date_ideas).map((idea, j) => (
                    <div key={j} className="flex items-start gap-2">
                      <span className="text-xs" style={{ color: '#f093fb' }}>✦</span>
                      <span className="text-sm" style={{ color: 'var(--color-text)' }}>{idea}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {a.timing_tip ? (
              <p className="text-xs p-3 rounded-xl" style={{ background: 'rgba(102,126,234,0.08)', color: '#a5b4fc' }}>
                ⏰ {s(a.timing_tip)}
              </p>
            ) : null}
          </motion.div>
        ))}
      </div>
    )
  }

  // ── comparison ─────────────────────────────────────────────
  const renderComparison = () => {
    const candidates = Array.isArray(result.candidates) ? (result.candidates as Record<string, unknown>[]) : []
    const dimensions = Array.isArray(result.dimensions) ? (result.dimensions as string[]) : []
    return (
      <div className="space-y-4">
        {candidates.map((c, i) => {
          const scores = (c.scores as Record<string, Record<string, unknown>>) ?? {}
          const totalScore = n(c.total_score)
          return (
            <motion.div key={s(c.candidate_id)} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
              className="glass-card p-5 space-y-4"
              style={s(c.candidate_id) === s(result.winner) ? { border: '1px solid rgba(251,191,36,0.4)' } : {}}>
              {s(c.candidate_id) === s(result.winner) ? (
                <div className="flex items-center gap-1">
                  <Trophy size={14} style={{ color: '#fbbf24' }} />
                  <span className="text-xs font-medium" style={{ color: '#fbbf24' }}>综合第一</span>
                </div>
              ) : null}
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-lg" style={{ color: 'var(--color-text)' }}>{s(c.candidate_name)}</h3>
                <span className="text-2xl font-bold text-gradient-primary">{totalScore}</span>
              </div>
              {dimensions.map(dim => {
                const val = scores[dim]
                if (!val) return null
                return (
                  <div key={dim} className="flex items-center gap-3">
                    <span className="text-xs w-16 flex-shrink-0" style={{ color: 'var(--color-text-secondary)' }}>{dim}</span>
                    <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.1)' }}>
                      <motion.div initial={{ width: 0 }} animate={{ width: `${n(val.score)}%` }}
                        transition={{ duration: 0.8, delay: i * 0.05 }} className="h-full rounded-full"
                        style={{ background: 'linear-gradient(90deg, #667eea, #f093fb)' }} />
                    </div>
                    <span className="text-xs w-8 text-right" style={{ color: '#f093fb' }}>{n(val.score)}</span>
                    <span className="text-xs flex-1 truncate" style={{ color: 'var(--color-text-secondary)' }}>{s(val.note)}</span>
                  </div>
                )
              })}
              {c.unique_advantage ? (
                <p className="text-xs p-2 rounded-xl" style={{ background: 'rgba(240,147,251,0.08)', color: '#f093fb' }}>
                  ✦ {s(c.unique_advantage)}
                </p>
              ) : null}
            </motion.div>
          )
        })}
        {result.winner_reason ? (
          <div className="glass-card p-4">
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              <span style={{ color: '#fbbf24' }}>🏆 推荐理由：</span>{s(result.winner_reason)}
            </p>
          </div>
        ) : null}
      </div>
    )
  }

  const TYPE_LABELS: Record<string, string> = {
    group_overview: '缘分总览',
    deep_compatibility: '深度相性分析',
    comm_advice: '沟通破冰建议',
    comparison: '横向对比报告',
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6 pb-24">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gradient-primary flex items-center gap-2">
            <Sparkles size={20} />
            {TYPE_LABELS[record.analysis_type] ?? '缘分分析'}
          </h1>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            {record.created_at?.slice(0, 16).replace('T', ' ')}
          </p>
        </div>
        <button onClick={() => setParamsDrawerOpen(true)}
          className="btn-ghost text-xs px-3 py-2 flex items-center gap-1"
          style={{ color: 'var(--color-text-secondary)' }}>
          <span>⚙</span>参数
        </button>
      </div>

      <AnimatePresence>
        {upgradeTarget ? (
          <UpgradeSelector
            candidateId={upgradeTarget}
            onSelect={handleUpgrade}
            onCancel={() => setUpgradeTarget(null)}
          />
        ) : null}
      </AnimatePresence>

      {launching ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }}>
          <div className="glass-card p-8 flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-2 border-transparent rounded-full animate-spin" style={{ borderTopColor: '#f093fb' }} />
            <p className="text-sm" style={{ color: 'var(--color-text)' }}>正在发起升级分析...</p>
          </div>
        </div>
      ) : null}

      {record.analysis_type === 'group_overview' && renderGroupOverview()}
      {record.analysis_type === 'deep_compatibility' && renderDeepCompatibility()}
      {record.analysis_type === 'comm_advice' && renderCommAdvice()}
      {record.analysis_type === 'comparison' && renderComparison()}

      <FateParamsDrawer
        open={paramsDrawerOpen}
        onClose={() => setParamsDrawerOpen(false)}
        params={matchParams}
        onChange={setMatchParams}
      />
    </div>
  )
}
