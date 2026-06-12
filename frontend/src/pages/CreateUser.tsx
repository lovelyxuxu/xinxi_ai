/**
 * 心犀AI - 注册/创建用户页（shadcn/ui 版）
 * ============================================
 *
 * 【shadcn/ui 改进点】
 * - Card 组件替代手写的 Section 容器
 * - Input / Textarea / Label / Select 组件替代原生表单元素
 * - Button 组件统一提交按钮样式
 * - ErrorAlert 替代手写错误提示
 *
 * 【学习要点 — react-hook-form + zod（进阶方向）】
 * 目前我们仍然使用 useState 管理表单（简单直接）。
 * 下一步可以升级为 react-hook-form + zod 验证：
 * - react-hook-form：更强大的表单状态管理，支持字段级错误
 * - zod：运行时类型验证，和 TypeScript 类型共享定义
 * - shadcn 的 Form 组件就是基于这两者构建的
 *
 * 但作为学习项目的第一步，useState 已经足够清晰。
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createUser } from '../api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ErrorAlert } from '@/components/ErrorAlert'
import type { UserCreate } from '@/types'

/** MBTI 类型选项 */
const MBTI_TYPES = ['INFP','INTP','INTJ','INFJ','ENFP','ENTP','ENTJ','ENFJ','ISFP','ISTP','ISTJ','ISFJ','ESFP','ESTP','ESTJ','ESFJ']

/** 学历选项 */
const EDUCATION_OPTIONS = ['高中','大专','本科','硕士','博士']

export default function CreateUser() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState<UserCreate>({
    nickname: '', gender: 'female', age: 25, city: '', province: '',
    education: '本科', annual_income: '未填写', marital_status: '未婚',
    target_gender: 'male', target_age_min: 22, target_age_max: 35,
    target_city: '不限', about_me: '', ideal_partner: '', hobbies: '', mbti: '未知',
  })

  const updateField = <K extends keyof UserCreate>(field: K, value: UserCreate[K]) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)
    if (!form.nickname || !form.city || !form.province) { setError('请填写昵称、城市和省份'); return }
    if (form.about_me.length < 10) { setError('"关于我"至少需要 10 个字符'); return }
    if (form.ideal_partner.length < 10) { setError('"理想的Ta"至少需要 10 个字符'); return }

    setLoading(true)
    try {
      const res = await createUser(form)
      navigate(`/user/${res.data.user_id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">✨ 加入心犀AI</h1>
        <p className="text-muted-foreground">填写你的资料，让 AI 红娘为你寻找缘分</p>
      </div>

      {error && <ErrorAlert message={error} className="mb-6" />}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 基础信息 */}
        <Card className="border-border/50">
          <CardHeader><CardTitle>👤 基础信息</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>昵称 <span className="text-rose-400">*</span></Label>
              <Input value={form.nickname} onChange={e => updateField('nickname', e.target.value)} placeholder="你的昵称" />
            </div>
            <div className="space-y-2">
              <Label>性别 <span className="text-rose-400">*</span></Label>
              <Select value={form.gender} onValueChange={(v) => updateField('gender', v as 'male' | 'female')}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="female">♀ 女生</SelectItem>
                  <SelectItem value="male">♂ 男生</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>年龄 <span className="text-rose-400">*</span></Label>
              <Input type="number" value={form.age} min={18} max={80} onChange={e => updateField('age', parseInt(e.target.value))} />
            </div>
            <div className="space-y-2">
              <Label>MBTI</Label>
              <Select value={form.mbti} onValueChange={(v) => updateField('mbti', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="未知">未知</SelectItem>
                  {MBTI_TYPES.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* 地理信息 */}
        <Card className="border-border/50">
          <CardHeader><CardTitle>📍 地理信息</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>城市 <span className="text-rose-400">*</span></Label>
              <Input value={form.city} onChange={e => updateField('city', e.target.value)} placeholder="如：杭州" />
            </div>
            <div className="space-y-2">
              <Label>省份 <span className="text-rose-400">*</span></Label>
              <Input value={form.province} onChange={e => updateField('province', e.target.value)} placeholder="如：浙江" />
            </div>
            <div className="space-y-2">
              <Label>学历</Label>
              <Select value={form.education} onValueChange={(v) => updateField('education', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {EDUCATION_OPTIONS.map(e => <SelectItem key={e} value={e}>{e}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* 自我介绍 */}
        <Card className="border-border/50">
          <CardHeader><CardTitle>💬 自我介绍</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>关于我（至少10字） <span className="text-rose-400">*</span></Label>
              <Textarea value={form.about_me} onChange={e => updateField('about_me', e.target.value)} placeholder="描述你的性格、生活方式、兴趣爱好..." className="h-24 resize-none" />
            </div>
            <div className="space-y-2">
              <Label>兴趣爱好（逗号分隔）</Label>
              <Input value={form.hobbies} onChange={e => updateField('hobbies', e.target.value)} placeholder="阅读,旅行,摄影,烹饪" />
            </div>
          </CardContent>
        </Card>

        {/* 择偶要求 */}
        <Card className="border-border/50">
          <CardHeader><CardTitle>💕 理想的Ta</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>描述你理想中的另一半（至少10字） <span className="text-rose-400">*</span></Label>
              <Textarea value={form.ideal_partner} onChange={e => updateField('ideal_partner', e.target.value)} placeholder="描述你期望的性格、三观、生活方式..." className="h-24 resize-none" />
            </div>
            <div className="grid grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>期望性别</Label>
                <Select value={form.target_gender} onValueChange={(v) => updateField('target_gender', v as 'male' | 'female')}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="female">♀ 女生</SelectItem>
                    <SelectItem value="male">♂ 男生</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>最小年龄</Label>
                <Input type="number" value={form.target_age_min} min={18} max={80} onChange={e => updateField('target_age_min', parseInt(e.target.value))} />
              </div>
              <div className="space-y-2">
                <Label>最大年龄</Label>
                <Input type="number" value={form.target_age_max} min={18} max={80} onChange={e => updateField('target_age_max', parseInt(e.target.value))} />
              </div>
              <div className="space-y-2">
                <Label>期望城市</Label>
                <Input value={form.target_city} onChange={e => updateField('target_city', e.target.value)} placeholder="不限" />
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center pt-4">
          <Button type="submit" disabled={loading} className="px-10 py-6 bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-600 hover:to-pink-600 rounded-full text-lg shadow-lg shadow-rose-200">
            {loading ? '正在创建...' : '✨ 创建账号'}
          </Button>
        </div>
      </form>
    </div>
  )
}
