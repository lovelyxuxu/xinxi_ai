/**
 * 心动清单页（FateList）
 * =======================
 * 展示用户加入的"心动 TA 们"列表，支持：
 * - 移除候选者
 * - 勾选多人发起群体缘分分析
 * - 单人立即缘分分析
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Heart, Trash2, Sparkles, ChevronRight, Users } from 'lucide-react'
import { getFateCandidates, removeFateCandidate, createFateAnalysis } from '@/api/client'
import type { FateCandidateItem } from '@/types'

// 星座 emoji 映射
const ZODIAC_EMOJI: Record<string, string> = {
  白羊座: '♈', 金牛座: '♉', 双子座: '♊', 巨蟹座: '♋',
  狮子座: '♌', 处女座: '♍', 天秤座: '♎', 天蝎座: '♏',
  射手座: '♐', 摩羯座: '♑', 水瓶座: '♒', 双鱼座: '♓',
}

export default function FateList() {
  const navigate = useNavigate()
  const [items, setItems] = useState<FateCandidateItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getFateCandidates()
      setItems(res.data.items)
    } catch {
      setError('获取心动清单失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleRemove = async (candidateId: string) => {
    try {
      await removeFateCandidate(candidateId)
      setItems(prev => prev.filter(i => i.candidate_id !== candidateId))
      setSelected(prev => { const s = new Set(prev); s.delete(candidateId); return s })
    } catch {
      setError('移除失败，请稍后重试')
    }
  }

  const toggleSelect = (candidateId: string) => {
    setSelected(prev => {
      const s = new Set(prev)
      s.has(candidateId) ? s.delete(candidateId) : s.add(candidateId)
      return s
    })
  }

  const handleGroupAnalysis = async () => {
    const ids = selected.size > 0 ? Array.from(selected) : items.map(i => i.candidate_id)
    if (ids.length === 0) return
    setAnalyzing(true)
    try {
      const res = await createFateAnalysis({
        analysis_type: 'group_overview',
        candidate_ids: ids,
      })
      navigate(`/fate/analysis/${res.data.analysis_id}`)
    } catch {
      setError('发起分析失败，请检查是否已完善个人资料')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSingleAnalysis = async (candidateId: string) => {
    setAnalyzing(true)
    try {
      const res = await createFateAnalysis({
        analysis_type: 'group_overview',
        candidate_ids: [candidateId],
      })
      navigate(`/fate/analysis/${res.data.analysis_id}`)
    } catch {
      setError('发起分析失败，请检查是否已完善个人资料')
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-64 gap-3">
        <div className="w-8 h-8 border-2 border-transparent rounded-full animate-spin" style={{ borderTopColor: '#f093fb' }} />
        <span style={{ color: 'var(--color-text-secondary)' }} className="text-sm">加载心动清单...</span>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient-primary flex items-center gap-2">
            <Heart size={24} className="fill-current" style={{ color: '#f093fb' }} />
            心动 TA 们
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            {items.length > 0 ? `${items.length} 位心动对象` : '还没有心动的人'}
          </p>
        </div>
        {items.length > 0 && (
          <button
            onClick={handleGroupAnalysis}
            disabled={analyzing}
            className="btn-primary flex items-center gap-2 text-sm px-4 py-2"
          >
            <Sparkles size={16} />
            {selected.size > 0 ? `分析选中(${selected.size})` : '全部分析'}
            {analyzing && <div className="w-3 h-3 border border-white/40 border-t-white rounded-full animate-spin" />}
          </button>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-3 border-red-500/30 text-red-400 text-sm"
        >
          {error}
        </motion.div>
      )}

      {/* 空状态 */}
      {items.length === 0 && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 gap-4"
        >
          <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'rgba(240,147,251,0.1)' }}>
            <Heart size={32} style={{ color: '#f093fb' }} />
          </div>
          <div className="text-center">
            <p className="font-medium" style={{ color: 'var(--color-text)' }}>还没有心动对象</p>
            <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              去发现页点击 ♡ 将喜欢的人加入心动清单
            </p>
          </div>
          <button className="btn-primary text-sm px-6" onClick={() => navigate('/')}>
            去发现
          </button>
        </motion.div>
      )}

      {/* 提示：勾选多人 */}
      {items.length > 1 && (
        <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
          <Users size={12} className="inline mr-1" />
          点击卡片可选中，勾选多人后统一进行缘分分析
        </p>
      )}

      {/* 心动列表 */}
      <AnimatePresence>
        {items.map((item, i) => {
          const u = item.candidate
          const isSelected = selected.has(item.candidate_id)
          const zodiacEmoji = u.zodiac_sign ? (ZODIAC_EMOJI[u.zodiac_sign] ?? '✦') : null

          return (
            <motion.div
              key={item.candidate_id}
              layout
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20, height: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => toggleSelect(item.candidate_id)}
              className={`glass-card p-4 cursor-pointer transition-all duration-200 ${
                isSelected ? 'ring-2' : ''
              }`}
              style={isSelected ? { '--tw-ring-color': '#f093fb' } as React.CSSProperties : {}}
            >
              <div className="flex items-center gap-3">
                {/* 选中指示器 */}
                <div
                  className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all"
                  style={{
                    borderColor: isSelected ? '#f093fb' : 'var(--color-border)',
                    background: isSelected ? '#f093fb' : 'transparent',
                  }}
                >
                  {isSelected && <span className="text-white text-xs">✓</span>}
                </div>

                {/* 头像 */}
                <div
                  className="w-12 h-12 rounded-full flex-shrink-0 overflow-hidden"
                  style={{ background: 'var(--color-surface-2)' }}
                >
                  {u.avatar_url ? (
                    <img src={u.avatar_url} alt={u.nickname} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-lg">
                      {u.gender === '女' ? '👩' : '👨'}
                    </div>
                  )}
                </div>

                {/* 用户信息 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold truncate" style={{ color: 'var(--color-text)' }}>
                      {u.nickname}
                    </span>
                    {zodiacEmoji && (
                      <span className="badge badge-zodiac text-xs">{zodiacEmoji} {u.zodiac_sign}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    {u.age && <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{u.age}岁</span>}
                    {u.city && <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>📍{u.city}</span>}
                    {u.mbti && <span className="text-xs badge" style={{ background: 'rgba(102,126,234,0.2)', color: '#a5b4fc' }}>{u.mbti}</span>}
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                  {/* 单人分析 */}
                  <button
                    className="p-2 rounded-xl transition-all hover:scale-105 flex items-center gap-1 text-xs font-medium"
                    style={{ background: 'rgba(240,147,251,0.15)', color: '#f093fb' }}
                    onClick={() => handleSingleAnalysis(item.candidate_id)}
                    title="立即缘分分析"
                  >
                    <Sparkles size={14} />
                    <span className="hidden sm:inline">分析</span>
                  </button>
                  {/* 查看资料 */}
                  <button
                    className="p-2 rounded-xl transition-all hover:scale-105"
                    style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--color-text-secondary)' }}
                    onClick={() => navigate(`/profile/${item.candidate_id}`)}
                    title="查看资料"
                  >
                    <ChevronRight size={16} />
                  </button>
                  {/* 移除 */}
                  <button
                    className="p-2 rounded-xl transition-all hover:scale-105"
                    style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}
                    onClick={() => handleRemove(item.candidate_id)}
                    title="移出清单"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* 关于他/她 */}
              {u.about_me && (
                <p className="text-xs mt-2 pl-8 line-clamp-2" style={{ color: 'var(--color-text-secondary)' }}>
                  {u.about_me}
                </p>
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>

      {/* 底部批量操作栏 */}
      {selected.size > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="fixed bottom-20 left-1/2 -translate-x-1/2 z-30"
        >
          <div
            className="flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl"
            style={{ background: 'rgba(15,12,41,0.95)', backdropFilter: 'blur(20px)', border: '1px solid rgba(240,147,251,0.3)' }}
          >
            <span className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
              已选 <span style={{ color: '#f093fb' }}>{selected.size}</span> 人
            </span>
            <button
              className="btn-primary text-sm px-4 py-2 flex items-center gap-2"
              onClick={handleGroupAnalysis}
              disabled={analyzing}
            >
              <Sparkles size={14} />
              统一缘分分析
            </button>
            <button
              className="btn-ghost text-sm px-3 py-2"
              onClick={() => setSelected(new Set())}
            >
              取消
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
