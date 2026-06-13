/**
 * 心犀AI - 注册页（v3 简化版）
 * ================================
 * 只需 4 个字段：昵称、性别、手机号、密码。
 * 其他资料可以注册后在个人中心完善，解锁「寻找缘分」。
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { Sparkles, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

interface RegisterForm {
  nickname: string
  gender: '男' | '女'
  phone: string
  password: string
}

export default function Register() {
  const { register: authRegister } = useAuth()
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [apiError, setApiError] = useState('')

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ defaultValues: { gender: '女' } })

  const selectedGender = watch('gender')

  const onSubmit = async (data: RegisterForm) => {
    setApiError('')
    try {
      await authRegister(data)
      navigate('/')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setApiError(e?.response?.data?.detail || e?.message || '注册失败，请稍后重试')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        className="glass-card w-full max-w-sm p-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* 标题 */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Sparkles size={24} style={{ color: '#f093fb' }} />
            <span className="text-2xl font-bold text-gradient-primary">加入心犀</span>
          </div>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            注册后完善资料，解锁寻找缘分 ✨
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* 昵称 */}
          <div>
            <label className="block text-sm font-medium mb-1.5">昵称</label>
            <input
              className="input-dark"
              placeholder="2-20 个字符"
              {...register('nickname', { required: '请填写昵称', minLength: { value: 2, message: '至少 2 个字符' }, maxLength: { value: 20, message: '最多 20 个字符' } })}
            />
            {errors.nickname && (
              <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{errors.nickname.message}</p>
            )}
          </div>

          {/* 性别 */}
          <div>
            <label className="block text-sm font-medium mb-1.5">性别</label>
            <div className="grid grid-cols-2 gap-3">
              {(['男', '女'] as const).map((g) => (
                <label
                  key={g}
                  className="flex items-center justify-center gap-2 p-3 rounded-xl border cursor-pointer transition-all"
                  style={{
                    borderColor: selectedGender === g ? 'rgba(102, 126, 234, 0.6)' : 'var(--color-border)',
                    background: selectedGender === g ? 'rgba(102, 126, 234, 0.12)' : 'rgba(255,255,255,0.04)',
                  }}
                  onClick={() => setValue('gender', g)}
                >
                  <span className="text-lg">{g === '男' ? '👨' : '👩'}</span>
                  <span className="font-medium">{g}</span>
                  <input type="radio" value={g} className="sr-only" {...register('gender', { required: true })} />
                </label>
              ))}
            </div>
          </div>

          {/* 手机号 */}
          <div>
            <label className="block text-sm font-medium mb-1.5">手机号</label>
            <input
              className="input-dark"
              placeholder="11 位大陆手机号"
              type="tel"
              maxLength={11}
              {...register('phone', {
                required: '请填写手机号',
                pattern: { value: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' },
              })}
            />
            {errors.phone && (
              <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{errors.phone.message}</p>
            )}
          </div>

          {/* 密码 */}
          <div>
            <label className="block text-sm font-medium mb-1.5">密码</label>
            <div className="relative">
              <input
                className="input-dark pr-10"
                placeholder="至少 8 位"
                type={showPassword ? 'text' : 'password'}
                {...register('password', {
                  required: '请设置密码',
                  minLength: { value: 8, message: '密码至少 8 位' },
                })}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2"
                style={{ color: 'var(--color-text-muted)' }}
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && (
              <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{errors.password.message}</p>
            )}
          </div>

          {/* API 错误 */}
          {apiError && (
            <div className="p-3 rounded-xl text-sm" style={{ background: 'rgba(248, 113, 113, 0.12)', border: '1px solid rgba(248, 113, 113, 0.3)', color: 'var(--color-danger)' }}>
              {apiError}
            </div>
          )}

          {/* 提交按钮 */}
          <button
            type="submit"
            className="btn-primary w-full mt-2"
            style={{ padding: '12px' }}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                注册中...
              </span>
            ) : (
              '立即注册'
            )}
          </button>
        </form>

        {/* 底部跳转 */}
        <p className="text-center text-sm mt-6" style={{ color: 'var(--color-text-secondary)' }}>
          已有账号？{' '}
          <Link to="/login" className="text-gradient-primary font-medium">
            立即登录
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
