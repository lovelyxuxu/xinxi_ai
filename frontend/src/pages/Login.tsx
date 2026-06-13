/**
 * 心犀AI - 登录页（与注册页风格对齐）
 */
import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { Sparkles, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

interface LoginForm {
  account: string
  password: string
}

export default function Login() {
  const { login, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [showPassword, setShowPassword] = useState(false)
  const [apiError, setApiError] = useState('')

  const redirectTo = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    defaultValues: { account: '', password: '' },
  })

  const onSubmit = async (data: LoginForm) => {
    setApiError('')
    try {
      await login(data)
      navigate(redirectTo, { replace: true })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setApiError(e?.response?.data?.detail || e?.message || '登录失败，请检查账号和密码')
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
            <span className="text-2xl font-bold text-gradient-primary">欢迎回来</span>
          </div>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            登录心犀AI，继续寻找你的缘分 💕
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* 账号 */}
          <div>
            <label className="block text-sm font-medium mb-1.5">手机号 / 用户ID</label>
            <input
              className="input-dark"
              placeholder="输入手机号或用户ID"
              autoComplete="username"
              {...register('account', { required: '请填写账号' })}
            />
            {errors.account && (
              <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>
                {errors.account.message}
              </p>
            )}
          </div>

          {/* 密码 */}
          <div>
            <label className="block text-sm font-medium mb-1.5">密码</label>
            <div className="relative">
              <input
                className="input-dark pr-10"
                placeholder="输入密码"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                {...register('password', {
                  required: '请输入密码',
                  minLength: { value: 6, message: '密码至少6位' },
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
              <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>
                {errors.password.message}
              </p>
            )}
          </div>

          {/* API 错误 */}
          {apiError && (
            <div
              className="p-3 rounded-xl text-sm"
              style={{
                background: 'rgba(248, 113, 113, 0.12)',
                border: '1px solid rgba(248, 113, 113, 0.3)',
                color: 'var(--color-danger)',
              }}
            >
              {apiError}
            </div>
          )}

          {/* 提交按钮 */}
          <button
            type="submit"
            className="btn-primary w-full mt-2"
            style={{ padding: '12px' }}
            disabled={isSubmitting || isLoading}
          >
            {isSubmitting || isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                登录中...
              </span>
            ) : (
              '立即登录'
            )}
          </button>
        </form>

        {/* 底部跳转 */}
        <p className="text-center text-sm mt-6" style={{ color: 'var(--color-text-secondary)' }}>
          还没有账号？{' '}
          <Link to="/register" className="text-gradient-primary font-medium">
            立即注册
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
