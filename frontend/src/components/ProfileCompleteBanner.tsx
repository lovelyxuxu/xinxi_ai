/**
 * ProfileCompleteBanner - 资料未完善引导横幅
 * ============================================
 * 当登录用户的 profile_complete=false 时显示，
 * 引导用户前往编辑资料页面，解锁「寻找缘分」功能。
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

export default function ProfileCompleteBanner() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [dismissed, setDismissed] = useState(false)

  // 已完善资料、未登录、已关闭——不显示
  if (!user || user.profile_complete || dismissed) return null

  return (
    <div
      className="animate-fade-in-up mx-4 mt-3 rounded-2xl p-4 flex items-center gap-3"
      style={{
        background: 'linear-gradient(135deg, rgba(102,126,234,0.18), rgba(240,147,251,0.12))',
        border: '1px solid rgba(102,126,234,0.3)',
      }}
    >
      <Sparkles
        size={20}
        style={{ color: '#f093fb', flexShrink: 0 }}
        className="animate-pulse-heart"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">完善资料，解锁寻找缘分 ✨</p>
        <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--color-text-secondary)' }}>
          填写年龄、城市和自我介绍后即可被发现
        </p>
      </div>
      <button
        className="btn-primary text-xs flex-shrink-0"
        style={{ padding: '6px 16px', borderRadius: '20px' }}
        onClick={() => navigate('/profile/edit')}
      >
        去完善
      </button>
      <button
        className="p-1 rounded-lg transition-colors flex-shrink-0"
        style={{ color: 'var(--color-text-muted)' }}
        onClick={() => setDismissed(true)}
        aria-label="关闭"
      >
        <X size={16} />
      </button>
    </div>
  )
}
