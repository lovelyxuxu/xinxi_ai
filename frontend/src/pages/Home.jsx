/**
 * 心犀AI - 首页：用户浏览
 * 展示所有用户卡片，支持按性别和城市筛选，以及分页。
 *
 * 学习要点：
 * - useEffect + useState 组合实现数据获取
 * - 筛选和分页通过 URL 参数传递给后端
 */
import { useState, useEffect } from 'react'
import { getUsers } from '../api/client'
import UserCard from '../components/UserCard'

export default function Home() {
  const [users, setUsers] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 筛选条件
  const [genderFilter, setGenderFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')
  const pageSize = 12

  // 加载用户数据
  useEffect(() => {
    setLoading(true)
    setError(null)
    const filters = {}
    if (genderFilter) filters.gender = genderFilter
    if (cityFilter) filters.city = cityFilter

    getUsers(page, pageSize, filters)
      .then(res => {
        setUsers(res.data.users)
        setTotal(res.data.total)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [page, genderFilter, cityFilter])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div>
      {/* 页面标题 */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          💕 发现有缘人
        </h1>
        <p className="text-gray-500">
          浏览 {total} 位用户，找到你的心灵契合
        </p>
      </div>

      {/* 筛选栏 */}
      <div className="flex flex-wrap justify-center gap-3 mb-8">
        <select
          value={genderFilter}
          onChange={e => { setGenderFilter(e.target.value); setPage(1) }}
          className="px-4 py-2 rounded-full border border-rose-200 bg-white text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-rose-300"
        >
          <option value="">全部性别</option>
          <option value="female">♀ 女生</option>
          <option value="male">♂ 男生</option>
        </select>

        <select
          value={cityFilter}
          onChange={e => { setCityFilter(e.target.value); setPage(1) }}
          className="px-4 py-2 rounded-full border border-rose-200 bg-white text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-rose-300"
        >
          <option value="">全部城市</option>
          <option value="杭州">杭州</option>
          <option value="上海">上海</option>
          <option value="北京">北京</option>
          <option value="深圳">深圳</option>
          <option value="成都">成都</option>
        </select>
      </div>

      {/* 加载状态 */}
      {loading && (
        <div className="text-center py-20">
          <div className="text-4xl animate-heartbeat inline-block mb-4">💕</div>
          <p className="text-gray-400">正在寻找有缘人...</p>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="text-center py-20">
          <p className="text-red-400">⚠️ {error}</p>
          <p className="text-gray-400 text-sm mt-2">请确保后端服务已启动 (python run.py)</p>
        </div>
      )}

      {/* 用户卡片网格 */}
      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {users.map((user, i) => (
              <div key={user.user_id} style={{ animationDelay: `${i * 0.06}s` }}>
                <UserCard user={user} />
              </div>
            ))}
          </div>

          {/* 空状态 */}
          {users.length === 0 && (
            <div className="text-center py-20 text-gray-400">
              暂无用户，快去注册一个吧~
            </div>
          )}

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-4 mt-10">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-full bg-white border border-rose-200 text-sm text-gray-600 disabled:opacity-40 btn-press"
              >
                ← 上一页
              </button>
              <span className="text-sm text-gray-500">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 rounded-full bg-white border border-rose-200 text-sm text-gray-600 disabled:opacity-40 btn-press"
              >
                下一页 →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
