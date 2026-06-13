/**
 * 心犀AI - 登录页面
 * ====================
 *
 * 【学习要点 — 表单处理】
 * 使用 react-hook-form + zod 的组合：
 * - react-hook-form：管理表单状态（值、错误、提交）
 * - zod：定义校验规则（邮箱格式、密码长度等）
 * - @hookform/resolvers/zod：把两者连接起来
 *
 * 【学习要点 — 路由跳转】
 * - useNavigate() 返回一个函数，用于编程式导航
 * - useLocation().state 可以读取上一个页面传来的数据
 * - 登录成功后跳回来源页面（如果有），否则跳到首页
 */
import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'

// ============================================================
//  表单校验规则（zod schema）
// ============================================================

/**
 * 【学习要点】
 * z.object() 定义表单的校验规则：
 * - account: 非空字符串
 * - password: 至少6位
 * 如果校验不通过，zod 会返回错误信息，react-hook-form 自动显示
 */
const loginSchema = z.object({
  account: z.string().min(1, '请输入邮箱或用户ID'),
  password: z.string().min(6, '密码至少6位'),
})

// 从 zod schema 推导 TypeScript 类型
type LoginFormData = z.infer<typeof loginSchema>

// ============================================================
//  登录页面组件
// ============================================================

export default function Login() {
  const { login, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)

  // 登录成功后跳转的目标（来源页面或首页）
  const redirectTo = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'

  /**
   * 【学习要点】
   * useForm 的 zodResolver 把 zod schema 和 react-hook-form 连接：
   * - resolver: zodResolver(loginSchema) — 用 zod 做校验
   * - defaultValues — 表单初始值
   * - register — 绑定输入框到表单状态
   * - handleSubmit — 提交时先校验，通过后执行回调
   * - formState.errors — 校验错误信息
   */
  const {
    register: registerField,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    defaultValues: {
      account: '',
      password: '',
    },
  })

  /**
   * 表单提交处理
   */
  const onSubmit = async (data: LoginFormData) => {
    setError(null)
    try {
      await login(data)
      navigate(redirectTo, { replace: true })
    } catch (err: any) {
      // 提取后端返回的错误信息
      const msg = err?.response?.data?.detail || '登录失败，请检查账号和密码'
      setError(msg)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">
            <span className="mr-2">💕</span>
            欢迎回来
          </CardTitle>
          <CardDescription>登录心犀AI，继续寻找你的缘分</CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            {/* 错误提示 */}
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* 账号输入 */}
            <div className="space-y-2">
              <Label htmlFor="account">邮箱或用户ID</Label>
              <Input
                id="account"
                placeholder="输入邮箱或用户ID"
                {...registerField('account')}
              />
              {errors.account && (
                <p className="text-sm text-destructive">{errors.account.message}</p>
              )}
            </div>

            {/* 密码输入 */}
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="输入密码"
                {...registerField('password')}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
          </CardContent>

          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? '登录中...' : '登录'}
            </Button>
            <p className="text-sm text-muted-foreground">
              还没有账号？{' '}
              <Link to="/register" className="text-primary hover:underline">
                立即注册
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
