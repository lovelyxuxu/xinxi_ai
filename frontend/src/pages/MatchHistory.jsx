/**
 * 心犀AI - 匹配历史页
 * 选择一个用户，查看其所有历史匹配记录和推荐信。
 *
 * 学习要点：
 * - 两阶段数据加载：先选用户，再加载历史
 * - 可展开的推荐信展示
 */
import { useState, useEffect } from 'react'
import { getUsers, getMatchHistory } from '../api/client'
import { Link } from 'react-router-dom'

export default function MatchHistory() {
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(false)
  const [expandedLetter, setExpandedLetter] = useState(null)

  // 加载用户列表
  useEffect(() => {
    getUsers(1, 100).then(res => setUsers(res.data.users || [])).catch(() => {})
  }, [])

  // 加载选中用户的匹配历史
  useEffect(() => {
    if (!selectedUser) { setRecords([]); return }
    setLoading(true)
    getMatchHistory(selectedUser)
      .then(res => setRecords(res.data.records || []))
      .catch(() => setRecords([]))
      .finally(() => setLoading(false))
  }, [selectedUser])

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">📋 匹配历史</h1>
        <p className="text-gray-500">选择用户查看 AI 匹配记录和推荐信</p>
      </div>

      {/* 用户选择器 */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-rose-100/50 mb-6">
        <label className="block text-sm text-gray-600 mb-2">选择用户</label>
        <select
          value={selectedUser}
          onChange={e => setSelectedUser(e.target.value)}
          className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-rose-300"
        >
          <option value="">-- 请选择 --</option>
          {users.map(u => (
            <option key={u.user_id} value={u.user_id}>
              {u.nickname} ({u.gender === 'female' ? '♀' : '♂'} {u.age}岁 {u.city})
            </option>
          ))}
        </select>
      </div>

      {/* 加载中 */}
      {loading && (
        <div className="text-center py-12">
          <div className="text-3xl animate-heartbeat inline-block">💕</div>
          <p className="text-gray-400 mt-3">加载历史记录...</p>
        </div>
      )}

      {/* 无记录 */}
      {!loading && selectedUser && records.length === 0 && (
        <div className="text-center py-12 bg-white rounded-2xl border border-rose-100/50">
          <p className="text-gray-400">暂无匹配记录</p>
          <Link
            to={`/user/${selectedUser}`}
            className="inline-block mt-4 px-6 py-2 bg-rose-500 text-white rounded-full text-sm btn-press"
          >
            去发起匹配 →
          </Link>
        </div>
      )}

      {/* 历史记录列表 */}
      {!loading && records.length > 0 && (
        <div className="space-y-6">
          {records.map((record, ri) => (
            <div key={ri} className="bg-white rounded-2xl shadow-sm border border-rose-100/50 overflow-hidden animate-fade-in-up">
              {/* 记录头部 */}
              <div className="px-6 py-4 bg-gradient-to-r from-rose-50 to-pink-50 border-b border-rose-100/50">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm text-gray-500">
                      {record.created_at?.slice(0, 16).replace('T', ' ')}
                    </span>
                    <span className="ml-3 text-sm font-medium text-rose-500">
                      {record.candidates?.length || 0} 位推荐
                    </span>
                  </div>
                  <span className="text-lg font-bold text-rose-500">
                    最高 {Math.max(...(record.candidates?.map(c => c.score) || [0]))} 分
                  </span>
                </div>
              </div>

              {/* 候选人列表 */}
              <div className="p-6 space-y-4">
                {record.candidates?.map((cand, ci) => {
                  const letterKey = `${ri}-${ci}`
                  const isExpanded = expandedLetter === letterKey
                  const letter = record.match_letters?.[ci]

                  return (
                    <div key={ci} className="border border-gray-100 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <Link to={`/user/${cand.user_id}`} className="text-rose-500 hover:underline font-medium no-underline">
                            {cand.nickname}
                          </Link>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cand.score >= 80 ? 'bg-rose-100 text-rose-600' : cand.score >= 60 ? 'bg-amber-100 text-amber-600' : 'bg-gray-100 text-gray-500'}`}>
                            {cand.score}分
                          </span>
                        </div>
                        {letter && (
                          <button
                            onClick={() => setExpandedLetter(isExpanded ? null : letterKey)}
                            className="text-sm text-pink-400 hover:text-pink-600 btn-press"
                          >
                            {isExpanded ? '收起信件 ▲' : '💌 查看推荐信'}
                          </button>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{cand.reason}</p>

                      {/* 展开的推荐信 */}
                      {isExpanded && letter && (
                        <div className="mt-3 p-4 bg-gradient-to-br from-rose-50 to-pink-50 rounded-xl border border-rose-200/50">
                          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{letter}</p>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Agent 日志（可折叠） */}
              {record.agent_log && record.agent_log.length > 0 && (
                <details className="px-6 pb-4">
                  <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                    🤖 Agent 执行日志 ({record.agent_log.length} 条)
                  </summary>
                  <div className="mt-2 bg-gray-50 rounded-lg p-3 text-xs text-gray-500 font-mono space-y-1 max-h-48 overflow-y-auto">
                    {record.agent_log.map((log, li) => (
                      <div key={li}>{log}</div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
