/**
 * 心犀AI - 注册/创建用户页
 * 新用户填写个人资料和择偶要求的表单。
 *
 * 学习要点：
 * - 受控表单：用 useState 管理所有表单字段
 * - 表单验证：提交前检查必填字段
 * - 创建成功后自动跳转到用户详情页
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createUser } from '../api/client'

export default function CreateUser() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 表单数据
  const [form, setForm] = useState({
    nickname: '',
    gender: 'female',
    age: 25,
    city: '',
    province: '',
    education: '本科',
    annual_income: '未填写',
    marital_status: '未婚',
    target_gender: 'male',
    target_age_min: 22,
    target_age_max: 35,
    target_city: '不限',
    about_me: '',
    ideal_partner: '',
    hobbies: '',
    mbti: '未知',
  })

  // 更新表单字段
  const updateField = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  // 提交
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    // 简单验证
    if (!form.nickname || !form.city || !form.province) {
      setError('请填写昵称、城市和省份')
      return
    }
    if (form.about_me.length < 10) {
      setError('"关于我"至少需要 10 个字符')
      return
    }
    if (form.ideal_partner.length < 10) {
      setError('"理想的Ta"至少需要 10 个字符')
      return
    }

    setLoading(true)
    try {
      const res = await createUser(form)
      navigate(`/user/${res.data.user_id}`)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">✨ 加入心犀AI</h1>
        <p className="text-gray-500">填写你的资料，让 AI 红娘为你寻找缘分</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 rounded-xl p-4 mb-6 text-sm">
          ⚠️ {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 基础信息 */}
        <Section title="👤 基础信息">
          <div className="grid grid-cols-2 gap-4">
            <Field label="昵称" required>
              <input
                type="text" value={form.nickname}
                onChange={e => updateField('nickname', e.target.value)}
                className={inputClass} placeholder="你的昵称"
              />
            </Field>
            <Field label="性别" required>
              <select value={form.gender} onChange={e => updateField('gender', e.target.value)} className={inputClass}>
                <option value="female">♀ 女生</option>
                <option value="male">♂ 男生</option>
              </select>
            </Field>
            <Field label="年龄" required>
              <input
                type="number" value={form.age} min={18} max={80}
                onChange={e => updateField('age', parseInt(e.target.value))}
                className={inputClass}
              />
            </Field>
            <Field label="MBTI">
              <select value={form.mbti} onChange={e => updateField('mbti', e.target.value)} className={inputClass}>
                <option value="未知">未知</option>
                {['INFP','INTP','INTJ','INFJ','ENFP','ENTP','ENTJ','ENFJ','ISFP','ISTP','ISTJ','ISFJ','ESFP','ESTP','ESTJ','ESFJ'].map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </Field>
          </div>
        </Section>

        {/* 地理信息 */}
        <Section title="📍 地理信息">
          <div className="grid grid-cols-3 gap-4">
            <Field label="城市" required>
              <input type="text" value={form.city} onChange={e => updateField('city', e.target.value)} className={inputClass} placeholder="如：杭州" />
            </Field>
            <Field label="省份" required>
              <input type="text" value={form.province} onChange={e => updateField('province', e.target.value)} className={inputClass} placeholder="如：浙江" />
            </Field>
            <Field label="学历">
              <select value={form.education} onChange={e => updateField('education', e.target.value)} className={inputClass}>
                {['高中','大专','本科','硕士','博士'].map(e => <option key={e} value={e}>{e}</option>)}
              </select>
            </Field>
          </div>
        </Section>

        {/* 自我介绍 */}
        <Section title="💬 自我介绍">
          <Field label="关于我（至少10字）" required>
            <textarea
              value={form.about_me}
              onChange={e => updateField('about_me', e.target.value)}
              className={`${inputClass} h-24 resize-none`}
              placeholder="描述你的性格、生活方式、兴趣爱好..."
            />
          </Field>
          <Field label="兴趣爱好（逗号分隔）">
            <input
              type="text" value={form.hobbies}
              onChange={e => updateField('hobbies', e.target.value)}
              className={inputClass} placeholder="阅读,旅行,摄影,烹饪"
            />
          </Field>
        </Section>

        {/* 择偶要求 */}
        <Section title="💕 理想的Ta">
          <Field label="描述你理想中的另一半（至少10字）" required>
            <textarea
              value={form.ideal_partner}
              onChange={e => updateField('ideal_partner', e.target.value)}
              className={`${inputClass} h-24 resize-none`}
              placeholder="描述你期望的性格、三观、生活方式..."
            />
          </Field>
          <div className="grid grid-cols-4 gap-4">
            <Field label="期望性别">
              <select value={form.target_gender} onChange={e => updateField('target_gender', e.target.value)} className={inputClass}>
                <option value="female">♀ 女生</option>
                <option value="male">♂ 男生</option>
              </select>
            </Field>
            <Field label="最小年龄">
              <input type="number" value={form.target_age_min} min={18} max={80} onChange={e => updateField('target_age_min', parseInt(e.target.value))} className={inputClass} />
            </Field>
            <Field label="最大年龄">
              <input type="number" value={form.target_age_max} min={18} max={80} onChange={e => updateField('target_age_max', parseInt(e.target.value))} className={inputClass} />
            </Field>
            <Field label="期望城市">
              <input type="text" value={form.target_city} onChange={e => updateField('target_city', e.target.value)} className={inputClass} placeholder="不限" />
            </Field>
          </div>
        </Section>

        {/* 提交按钮 */}
        <div className="text-center pt-4">
          <button
            type="submit"
            disabled={loading}
            className="px-10 py-3 bg-gradient-to-r from-rose-500 to-pink-500 text-white rounded-full font-bold text-lg shadow-lg shadow-rose-200 hover:shadow-xl btn-press disabled:opacity-60 transition-all"
          >
            {loading ? '正在创建...' : '✨ 创建账号'}
          </button>
        </div>
      </form>
    </div>
  )
}

// ===== 通用样式和子组件 =====
const inputClass = 'w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-rose-300 focus:border-rose-300 transition-all'

function Section({ title, children }) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-rose-100/50">
      <h2 className="text-lg font-bold text-gray-800 mb-4">{title}</h2>
      <div className="space-y-4">{children}</div>
    </div>
  )
}

function Field({ label, required, children }) {
  return (
    <div>
      <label className="block text-sm text-gray-600 mb-1.5">
        {label} {required && <span className="text-rose-400">*</span>}
      </label>
      {children}
    </div>
  )
}
