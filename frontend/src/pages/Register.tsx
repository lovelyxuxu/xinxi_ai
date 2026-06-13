/**
 * 心犀AI - 注册页面
 * ====================
 *
 * 【学习要点 — 复杂表单】
 * 注册表单包含多个字段，分为几个区块：
 * 1. 基本信息（昵称、性别、年龄、城市）
 * 2. 择偶偏好（期望性别、年龄范围、城市）
 * 3. 自我介绍（关于我、理想的Ta）
 * 4. 认证信息（密码、邮箱）
 *
 * 使用 react-hook-form 管理所有字段状态，
 * zod 做客户端校验，后端也有校验（双重保障）。
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

// ============================================================
//  表单校验规则
// ============================================================

/**
 * 【学习要点】
 * z.object 中每个字段都可以链式调用校验方法：
 * - .min() / .max() — 字符串长度或数字范围
 * - .email() — 邮箱格式校验
 * - .optional() — 字段可以不填
 * - .refine() — 自定义校验逻辑（如：确认密码是否一致）
 */
const registerSchema = z.object({
  // 基本信息
  nickname: z.string().min(1, '请输入昵称').max(20, '昵称最多20个字符'),
  gender: z.string().min(1, '请选择性别'),
  age: z.coerce.number().min(18, '年龄至少18岁').max(80, '年龄最多80岁'),
  city: z.string().min(1, '请输入城市'),
  province: z.string().min(1, '请输入省份'),

  // 择偶偏好
  target_gender: z.string().min(1, '请选择期望性别'),
  target_age_min: z.coerce.number().min(18).max(80),
  target_age_max: z.coerce.number().min(18).max(80),
  target_city: z.string().optional().default('不限'),

  // 自我介绍
  about_me: z.string().min(10, '自我介绍至少10个字符'),
  ideal_partner: z.string().min(10, '理想对象描述至少10个字符'),
  hobbies: z.string().optional().default(''),

  // 认证信息
  password: z.string().min(6, '密码至少6位'),
  email: z.string().email('邮箱格式不正确').optional().or(z.literal('')),
})

type RegisterFormData = z.infer<typeof registerSchema>

// ============================================================
//  注册页面组件
// ============================================================

export default function Register() {
  const { register: authRegister, isLoading } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  const {
    register: registerField,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<RegisterFormData>({
    defaultValues: {
      nickname: '',
      gender: '',
      age: 25,
      city: '',
      province: '',
      target_gender: '',
      target_age_min: 18,
      target_age_max: 45,
      target_city: '不限',
      about_me: '',
      ideal_partner: '',
      hobbies: '',
      password: '',
      email: '',
    },
  })

  /**
   * 表单提交处理
   */
  const onSubmit = async (data: RegisterFormData) => {
    setError(null)
    try {
      await authRegister({
        ...data,
        // 确保可选字段有默认值
        education: '本科',
        annual_income: '未填写',
        marital_status: '未婚',
        mbti: '未知',
        email: data.email || undefined,
      })
      navigate('/', { replace: true })
    } catch (err: any) {
      const msg = err?.response?.data?.detail || '注册失败，请稍后重试'
      setError(msg)
    }
  }

  return (
    <div className="flex items-center justify-center py-8">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">
            <span className="mr-2">✨</span>
            创建你的缘分档案
          </CardTitle>
          <CardDescription>填写信息，开启你的寻缘之旅</CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-6">
            {/* 错误提示 */}
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* === 基本信息 === */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                基本信息
              </h3>

              <div className="grid grid-cols-2 gap-4">
                {/* 昵称 */}
                <div className="space-y-2">
                  <Label htmlFor="nickname">昵称 *</Label>
                  <Input id="nickname" placeholder="你的昵称" {...registerField('nickname')} />
                  {errors.nickname && <p className="text-sm text-destructive">{errors.nickname.message}</p>}
                </div>

                {/* 年龄 */}
                <div className="space-y-2">
                  <Label htmlFor="age">年龄 *</Label>
                  <Input id="age" type="number" {...registerField('age')} />
                  {errors.age && <p className="text-sm text-destructive">{errors.age.message}</p>}
                </div>

                {/* 性别 */}
                <div className="space-y-2">
                  <Label>性别 *</Label>
                  <Select onValueChange={(val) => setValue('gender', val)}>
                    <SelectTrigger>
                      <SelectValue placeholder="请选择" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">男</SelectItem>
                      <SelectItem value="female">女</SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.gender && <p className="text-sm text-destructive">{errors.gender.message}</p>}
                </div>

                {/* 城市 */}
                <div className="space-y-2">
                  <Label htmlFor="city">城市 *</Label>
                  <Input id="city" placeholder="所在城市" {...registerField('city')} />
                  {errors.city && <p className="text-sm text-destructive">{errors.city.message}</p>}
                </div>

                {/* 省份 */}
                <div className="space-y-2">
                  <Label htmlFor="province">省份 *</Label>
                  <Input id="province" placeholder="所在省份" {...registerField('province')} />
                  {errors.province && <p className="text-sm text-destructive">{errors.province.message}</p>}
                </div>
              </div>
            </div>

            {/* === 择偶偏好 === */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                择偶偏好
              </h3>

              <div className="grid grid-cols-2 gap-4">
                {/* 期望性别 */}
                <div className="space-y-2">
                  <Label>期望性别 *</Label>
                  <Select onValueChange={(val) => setValue('target_gender', val)}>
                    <SelectTrigger>
                      <SelectValue placeholder="请选择" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">男</SelectItem>
                      <SelectItem value="female">女</SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.target_gender && <p className="text-sm text-destructive">{errors.target_gender.message}</p>}
                </div>

                {/* 期望城市 */}
                <div className="space-y-2">
                  <Label htmlFor="target_city">期望城市</Label>
                  <Input id="target_city" placeholder="不限" {...registerField('target_city')} />
                </div>

                {/* 期望最小年龄 */}
                <div className="space-y-2">
                  <Label htmlFor="target_age_min">最小年龄</Label>
                  <Input id="target_age_min" type="number" {...registerField('target_age_min')} />
                </div>

                {/* 期望最大年龄 */}
                <div className="space-y-2">
                  <Label htmlFor="target_age_max">最大年龄</Label>
                  <Input id="target_age_max" type="number" {...registerField('target_age_max')} />
                </div>
              </div>
            </div>

            {/* === 自我介绍 === */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                自我介绍
              </h3>

              <div className="space-y-2">
                <Label htmlFor="about_me">关于我 *（至少10个字符）</Label>
                <Textarea id="about_me" placeholder="介绍一下你自己..." {...registerField('about_me')} />
                {errors.about_me && <p className="text-sm text-destructive">{errors.about_me.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="ideal_partner">理想的Ta *（至少10个字符）</Label>
                <Textarea id="ideal_partner" placeholder="你理想的另一半是什么样的..." {...registerField('ideal_partner')} />
                {errors.ideal_partner && <p className="text-sm text-destructive">{errors.ideal_partner.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="hobbies">兴趣爱好</Label>
                <Input id="hobbies" placeholder="阅读, 旅行, 美食..." {...registerField('hobbies')} />
              </div>
            </div>

            {/* === 认证信息 === */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                账号信息
              </h3>

              <div className="grid grid-cols-2 gap-4">
                {/* 密码 */}
                <div className="space-y-2">
                  <Label htmlFor="password">密码 *（至少6位）</Label>
                  <Input id="password" type="password" placeholder="设置密码" {...registerField('password')} />
                  {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
                </div>

                {/* 邮箱 */}
                <div className="space-y-2">
                  <Label htmlFor="email">邮箱（可选）</Label>
                  <Input id="email" type="email" placeholder="用于登录" {...registerField('email')} />
                  {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
                </div>
              </div>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? '注册中...' : '创建档案并登录'}
            </Button>
            <p className="text-sm text-muted-foreground">
              已有账号？{' '}
              <Link to="/login" className="text-primary hover:underline">
                立即登录
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
