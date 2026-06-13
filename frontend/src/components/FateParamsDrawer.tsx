/**
 * 缘分参数抽屉（FateParamsDrawer）
 * ==================================
 * 发起缘分分析前，允许用户临时调整匹配参数（不影响个人资料）。
 * 使用 Framer Motion 实现底部滑入动画。
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, SlidersHorizontal, RotateCcw } from 'lucide-react'
import type { MatchParams } from '@/types'

interface FateParamsDrawerProps {
  open: boolean
  onClose: () => void
  params: MatchParams
  onChange: (params: MatchParams) => void
}

const EDUCATION_OPTIONS = ['不限', '高中及以下', '大专', '本科', '硕士', '博士']
const CITY_OPTIONS = ['不限', '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '西安', '其他']

const DEFAULT_PARAMS: MatchParams = {
  target_age_min: 22,
  target_age_max: 35,
  target_city: '不限',
  target_height_min: 155,
  target_height_max: 185,
  target_education: '不限',
}

export default function FateParamsDrawer({ open, onClose, params, onChange }: FateParamsDrawerProps) {
  const [local, setLocal] = useState<MatchParams>({ ...DEFAULT_PARAMS, ...params })

  const handleApply = () => {
    onChange(local)
    onClose()
  }

  const handleReset = () => {
    setLocal(DEFAULT_PARAMS)
    onChange(DEFAULT_PARAMS)
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* 背景遮罩 */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
            onClick={onClose}
          />

          {/* 抽屉主体 */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
            className="fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl"
            style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
          >
            <div className="max-w-xl mx-auto px-5 py-6 space-y-5">
              {/* 顶部手柄 + 标题 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <SlidersHorizontal size={18} style={{ color: '#f093fb' }} />
                  <h3 className="font-bold text-lg" style={{ color: 'var(--color-text)' }}>
                    临时调整匹配参数
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleReset}
                    className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1"
                    title="重置为默认"
                  >
                    <RotateCcw size={12} />
                    重置
                  </button>
                  <button
                    onClick={onClose}
                    className="p-1.5 rounded-xl transition-colors"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>
              <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                仅对本次分析生效，不修改你的个人资料
              </p>

              {/* 年龄范围 */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  年龄范围：{local.target_age_min} - {local.target_age_max} 岁
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range" min={18} max={50} step={1}
                    value={local.target_age_min}
                    onChange={e => setLocal(p => ({ ...p, target_age_min: +e.target.value }))}
                    className="w-full accent-purple-500"
                  />
                  <input
                    type="range" min={18} max={60} step={1}
                    value={local.target_age_max}
                    onChange={e => setLocal(p => ({ ...p, target_age_max: +e.target.value }))}
                    className="w-full accent-pink-500"
                  />
                </div>
              </div>

              {/* 身高范围 */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                  身高范围：{local.target_height_min} - {local.target_height_max} cm
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range" min={145} max={190} step={1}
                    value={local.target_height_min}
                    onChange={e => setLocal(p => ({ ...p, target_height_min: +e.target.value }))}
                    className="w-full accent-purple-500"
                  />
                  <input
                    type="range" min={155} max={200} step={1}
                    value={local.target_height_max}
                    onChange={e => setLocal(p => ({ ...p, target_height_max: +e.target.value }))}
                    className="w-full accent-pink-500"
                  />
                </div>
              </div>

              {/* 城市偏好 */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>城市偏好</label>
                <div className="flex flex-wrap gap-2">
                  {CITY_OPTIONS.map(city => (
                    <button
                      key={city}
                      onClick={() => setLocal(p => ({ ...p, target_city: city }))}
                      className="px-3 py-1.5 rounded-xl text-sm transition-all"
                      style={{
                        background: local.target_city === city ? 'rgba(240,147,251,0.3)' : 'rgba(255,255,255,0.05)',
                        color: local.target_city === city ? '#f093fb' : 'var(--color-text-secondary)',
                        border: `1px solid ${local.target_city === city ? 'rgba(240,147,251,0.5)' : 'var(--color-border)'}`,
                      }}
                    >
                      {city}
                    </button>
                  ))}
                </div>
              </div>

              {/* 学历要求 */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>最低学历</label>
                <div className="flex flex-wrap gap-2">
                  {EDUCATION_OPTIONS.map(edu => (
                    <button
                      key={edu}
                      onClick={() => setLocal(p => ({ ...p, target_education: edu }))}
                      className="px-3 py-1.5 rounded-xl text-sm transition-all"
                      style={{
                        background: local.target_education === edu ? 'rgba(102,126,234,0.3)' : 'rgba(255,255,255,0.05)',
                        color: local.target_education === edu ? '#a5b4fc' : 'var(--color-text-secondary)',
                        border: `1px solid ${local.target_education === edu ? 'rgba(102,126,234,0.5)' : 'var(--color-border)'}`,
                      }}
                    >
                      {edu}
                    </button>
                  ))}
                </div>
              </div>

              {/* 应用按钮 */}
              <button
                onClick={handleApply}
                className="btn-primary w-full py-3 text-base font-semibold"
              >
                应用参数 · 开始分析
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
