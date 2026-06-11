/**
 * 心犀AI - 用户卡片组件
 * 在列表页中展示每位用户的概要信息。
 * 点击卡片跳转到用户详情页。
 *
 * 学习要点：
 * - 组件接收 props 展示数据，是 React 中最基础的模式
 * - 用 Tailwind 实现卡片样式：圆角、阴影、悬浮效果
 */
import { Link } from 'react-router-dom'

export default function UserCard({ user }) {
  // 根据性别选不同的渐变色
  const genderGradient = user.gender === 'female'
    ? 'from-pink-400 to-rose-400'
    : 'from-blue-400 to-indigo-400'

  const genderEmoji = user.gender === 'female' ? '♀' : '♂'

  return (
    <Link
      to={`/user/${user.user_id}`}
      className="block no-underline animate-fade-in-up"
    >
      <div className="bg-white rounded-2xl overflow-hidden shadow-sm card-hover border border-rose-100/50">
        {/* 顶部渐变色块 + 头像占位 */}
        <div className={`h-24 bg-gradient-to-br ${genderGradient} relative`}>
          <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 w-16 h-16 rounded-full bg-white shadow-lg flex items-center justify-center text-2xl border-3 border-white">
            {user.nickname?.charAt(0) || '?'}
          </div>
        </div>

        {/* 用户信息 */}
        <div className="pt-10 pb-5 px-5 text-center">
          <h3 className="text-lg font-bold text-gray-800 mb-1">
            {user.nickname}
            <span className={`ml-2 text-sm ${user.gender === 'female' ? 'text-pink-400' : 'text-blue-400'}`}>
              {genderEmoji}
            </span>
          </h3>
          <p className="text-sm text-gray-500 mb-3">
            {user.age}岁 · {user.city} · {user.education}
          </p>
          <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed px-2">
            {user.about_me}
          </p>

          {/* 兴趣标签 */}
          {user.hobbies && (
            <div className="flex flex-wrap justify-center gap-1.5 mt-3">
              {user.hobbies.split(',').slice(0, 4).map((hobby, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 bg-rose-50 text-rose-400 text-xs rounded-full"
                >
                  {hobby.trim()}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}
