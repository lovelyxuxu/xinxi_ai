/**
 * 心犀AI - 编辑资料页面
 * =======================
 *
 * 分三个 Tab：
 * 1. 基本信息：头像、昵称、年龄、城市、身高、学历等
 * 2. 择偶偏好：期望对方的性别、年龄、城市、学历
 * 3. 自我介绍：关于我、理想的Ta、兴趣爱好
 *
 * 学习要点 — 部分更新（Partial Update）:
 * - 使用 react-hook-form 的 formState.dirtyFields 追踪哪些字段被修改过
 * - 只发送 dirty 字段给后端（不发送未改变的字段）
 * - 减少网络传输，也避免意外覆盖其他客户端同时修改的字段
 *
 * 学习要点 — 乐观更新:
 * 保存成功后立即调用 updateUser(res.data)，
 * 全局 AuthContext 中的 user 状态同步更新，
 * 导航栏昵称/头像会立刻刷新，无需重新登录。
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, Controller } from 'react-hook-form'
import { motion } from 'framer-motion'
import { Save, ArrowLeft, CheckCircle, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import ImageUpload from '@/components/ImageUpload'
import { useAuth } from '@/contexts/AuthContext'
import { updateMe } from '@/api/client'
import type { AuthUser } from '@/types'

const EDUCATION_OPTIONS = ['高中及以下', '大专', '本科', '硕士', '博士']
const MBTI_OPTIONS = [
  'INTJ','INTP','ENTJ','ENTP',
  'INFJ','INFP','ENFJ','ENFP',
  'ISTJ','ISFJ','ESTJ','ESFJ',
  'ISTP','ISFP','ESTP','ESFP',
  '未知',
]
const INCOME_OPTIONS = ['未填写', '5万以下', '5-10万', '10-20万', '20-50万', '50万以上']
const MARITAL_OPTIONS = ['未婚', '离异', '丧偶']

type FormValues = {
  nickname: string
  age: number
  city: string
  province: string
  height_cm: number | null
  education: string
  annual_income: string
  marital_status: string
  mbti: string
  target_gender: string
  target_age_min: number
  target_age_max: number
  target_city: string
  target_height_min: number | null
  target_education: string
  about_me: string
  ideal_partner: string
  hobbies: string
}

export default function EditProfile() {
  const { user, updateUser } = useAuth()
  const navigate = useNavigate()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 头像和照片单独管理（通过 ImageUpload 组件直接上传，不走表单提交）
  const [avatarUrls, setAvatarUrls] = useState<string[]>(
    user?.avatar_url ? [user.avatar_url] : []
  )
  const [photos, setPhotos] = useState<string[]>(user?.photos || [])

  const {
    register,
    handleSubmit,
    control,
    formState: { dirtyFields },
  } = useForm<FormValues>({
    defaultValues: {
      nickname: user?.nickname ?? '',
      age: user?.age ?? 25,
      city: user?.city ?? '',
      province: user?.province ?? '',
      height_cm: user?.height_cm ?? null,
      education: user?.education ?? '本科',
      annual_income: user?.annual_income ?? '未填写',
      marital_status: user?.marital_status ?? '未婚',
      mbti: user?.mbti ?? '未知',
      target_gender: user?.target_gender ?? 'female',
      target_age_min: user?.target_age_min ?? 20,
      target_age_max: user?.target_age_max ?? 35,
      target_city: user?.target_city ?? '不限',
      target_height_min: user?.target_height_min ?? null,
      target_education: user?.target_education ?? '',
      about_me: user?.about_me ?? '',
      ideal_partner: user?.ideal_partner ?? '',
      hobbies: user?.hobbies ?? '',
    },
  })

  const onSubmit = async (data: FormValues) => {
    setSaving(true)
    setError(null)

    try {
      // 只发送 dirty 字段（用户实际修改过的字段）
      const changed = Object.fromEntries(
        Object.entries(data).filter(([k]) => dirtyFields[k as keyof typeof dirtyFields])
      )

      if (Object.keys(changed).length > 0) {
        const res = await updateMe(changed as Partial<AuthUser>)
        // 同步更新全局 AuthContext 中的用户信息
        updateUser(res.data)
      }

      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err?.response?.data?.detail ?? '保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  // 头像上传后同步更新 AuthContext
  const handleAvatarChange = (urls: string[]) => {
    setAvatarUrls(urls)
    updateUser({ avatar_url: urls[0] || null })
  }

  // 照片上传后同步更新 AuthContext
  const handlePhotosChange = (urls: string[]) => {
    setPhotos(urls)
    updateUser({ photos: urls })
  }

  return (
    <div className="max-w-lg mx-auto space-y-4 pb-24 md:pb-8">
      {/* 页头 */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate(-1)}
          className="text-muted-foreground hover:text-foreground h-8 w-8"
        >
          <ArrowLeft size={18} />
        </Button>
        <h1 className="text-lg font-semibold">编辑资料</h1>

        {/* 保存成功提示 */}
        {saved && (
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            className="ml-auto flex items-center gap-1 text-sm text-green-400"
          >
            <CheckCircle size={14} />
            已保存
          </motion.div>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
          <AlertCircle size={16} className="flex-shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        <Tabs defaultValue="basic" className="space-y-4">
          <TabsList className="grid grid-cols-3 w-full bg-card border border-border">
            <TabsTrigger value="basic" className="text-xs data-[state=active]:bg-primary/15 data-[state=active]:text-primary">
              基本信息
            </TabsTrigger>
            <TabsTrigger value="preference" className="text-xs data-[state=active]:bg-primary/15 data-[state=active]:text-primary">
              择偶偏好
            </TabsTrigger>
            <TabsTrigger value="intro" className="text-xs data-[state=active]:bg-primary/15 data-[state=active]:text-primary">
              自我介绍
            </TabsTrigger>
          </TabsList>

          {/* ===== 基本信息 ===== */}
          <TabsContent value="basic" className="space-y-4 mt-2">
            <div className="glass-card p-4 space-y-4">
              {/* 头像 */}
              <div className="flex flex-col items-center gap-2 py-2">
                <ImageUpload
                  value={avatarUrls}
                  onChange={handleAvatarChange}
                  maxCount={1}
                  isAvatar
                />
                <span className="text-xs text-muted-foreground">点击更换头像</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <Field label="昵称">
                  <Input className="input-dark" {...register('nickname')} />
                </Field>
                <Field label="年龄">
                  <Input type="number" className="input-dark" {...register('age', { valueAsNumber: true })} />
                </Field>
                <Field label="城市">
                  <Input className="input-dark" {...register('city')} />
                </Field>
                <Field label="省份">
                  <Input className="input-dark" {...register('province')} />
                </Field>
                <Field label="身高 (cm)">
                  <Input
                    type="number"
                    className="input-dark"
                    placeholder="选填"
                    {...register('height_cm', {
                      setValueAs: v => v === '' ? null : Number(v),
                    })}
                  />
                </Field>
                <Field label="婚姻状况">
                  <Controller
                    name="marital_status"
                    control={control}
                    render={({ field }) => (
                      <SelectField options={MARITAL_OPTIONS} value={field.value} onChange={field.onChange} />
                    )}
                  />
                </Field>
                <Field label="学历">
                  <Controller
                    name="education"
                    control={control}
                    render={({ field }) => (
                      <SelectField options={EDUCATION_OPTIONS} value={field.value} onChange={field.onChange} />
                    )}
                  />
                </Field>
                <Field label="年收入">
                  <Controller
                    name="annual_income"
                    control={control}
                    render={({ field }) => (
                      <SelectField options={INCOME_OPTIONS} value={field.value} onChange={field.onChange} />
                    )}
                  />
                </Field>
                <Field label="MBTI" className="col-span-2">
                  <Controller
                    name="mbti"
                    control={control}
                    render={({ field }) => (
                      <SelectField options={MBTI_OPTIONS} value={field.value} onChange={field.onChange} placeholder="选择 MBTI" />
                    )}
                  />
                </Field>
              </div>
            </div>

            {/* 照片上传 */}
            <div className="glass-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">我的照片</Label>
                <span className="text-xs text-muted-foreground">最多 6 张</span>
              </div>
              <ImageUpload value={photos} onChange={handlePhotosChange} maxCount={6} />
            </div>
          </TabsContent>

          {/* ===== 择偶偏好 ===== */}
          <TabsContent value="preference" className="space-y-4 mt-2">
            <div className="glass-card p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Field label="期望性别">
                  <Controller
                    name="target_gender"
                    control={control}
                    render={({ field }) => (
                      <SelectField
                        options={[
                          { value: 'female', label: '女性' },
                          { value: 'male', label: '男性' },
                        ]}
                        value={field.value}
                        onChange={field.onChange}
                      />
                    )}
                  />
                </Field>
                <Field label="期望城市">
                  <Input className="input-dark" placeholder="不限" {...register('target_city')} />
                </Field>
                <Field label="年龄下限">
                  <Input type="number" className="input-dark" {...register('target_age_min', { valueAsNumber: true })} />
                </Field>
                <Field label="年龄上限">
                  <Input type="number" className="input-dark" {...register('target_age_max', { valueAsNumber: true })} />
                </Field>
                <Field label="身高下限 (cm)">
                  <Input
                    type="number"
                    className="input-dark"
                    placeholder="不限"
                    {...register('target_height_min', {
                      setValueAs: v => v === '' ? null : Number(v),
                    })}
                  />
                </Field>
                <Field label="最低学历">
                  <Controller
                    name="target_education"
                    control={control}
                    render={({ field }) => (
                      <SelectField
                        options={['不限', ...EDUCATION_OPTIONS]}
                        value={field.value || '不限'}
                        onChange={v => field.onChange(v === '不限' ? '' : v)}
                        placeholder="不限"
                      />
                    )}
                  />
                </Field>
              </div>
            </div>
          </TabsContent>

          {/* ===== 自我介绍 ===== */}
          <TabsContent value="intro" className="space-y-4 mt-2">
            <div className="glass-card p-4 space-y-4">
              <Field label="关于我">
                <Textarea
                  className="input-dark min-h-[100px] resize-none"
                  placeholder="介绍一下自己的性格、生活方式..."
                  {...register('about_me')}
                />
              </Field>
              <Field label="理想的Ta">
                <Textarea
                  className="input-dark min-h-[100px] resize-none"
                  placeholder="描述你心目中的另一半..."
                  {...register('ideal_partner')}
                />
              </Field>
              <Field label="兴趣爱好">
                <Input
                  className="input-dark"
                  placeholder="例如：旅行、摄影、咖啡（用逗号分隔）"
                  {...register('hobbies')}
                />
              </Field>
            </div>
          </TabsContent>
        </Tabs>

        {/* 保存按钮 */}
        <Button
          type="submit"
          disabled={saving || Object.keys(dirtyFields).length === 0}
          className="w-full mt-4 h-12 bg-gradient-primary text-white border-0 rounded-xl font-medium shadow-lg shadow-primary/30 hover:opacity-90 disabled:opacity-50"
        >
          {saving ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              保存中...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Save size={18} />
              保存资料
            </span>
          )}
        </Button>
      </form>
    </div>
  )
}

// ===== 辅助组件 =====

function Field({
  label,
  children,
  className,
}: {
  label: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`space-y-1.5 ${className ?? ''}`}>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  )
}

function SelectField({
  options,
  value,
  onChange,
  placeholder,
}: {
  options: string[] | { value: string; label: string }[]
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  const normalized = options.map(o =>
    typeof o === 'string' ? { value: o, label: o } : o
  )
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="input-dark h-9 text-sm">
        <SelectValue placeholder={placeholder ?? '请选择'} />
      </SelectTrigger>
      <SelectContent className="bg-card border-border">
        {normalized.map(o => (
          <SelectItem key={o.value} value={o.value} className="text-sm">
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
