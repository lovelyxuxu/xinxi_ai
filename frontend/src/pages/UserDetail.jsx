/**
 * 心犀AI - 用户详情页 + 匹配（v2: WebSocket 实时进度版）
 * ============================================================
 * 展示用户完整资料，并通过 WebSocket 实时展示 AI 匹配进度。
 *
 * 学习要点：
 * ---------
 * WebSocket 通信流程：
 *   1. 前端 new WebSocket(url) 建立连接
 *   2. 后端逐节点推送事件（node_start → node_end → ... → complete）
 *   3. 前端实时更新进度条和日志
 *   4. 后端推送 complete 事件，包含最终匹配结果
 *   5. 连接关闭
 *
 * 与 HTTP 的区别：
 *   - HTTP：请求→等很久→一次性返回（用户不知道在干嘛）
 *   - WebSocket：连接后持续收到消息，用户体验更好
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getUser, getMatchHistory } from '../api/client'

export default function UserDetail() {
  const { userId } = useParams()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [matchResult, setMatchResult] = useState(null)
  const [history, setHistory] = useState([])
  const [activeTab, setActiveTab] = useState('profile')
  const [error, setError] = useState(null)

  // WebSocket 相关状态
  const [wsStatus, setWsStatus] = useState('idle') // idle | connecting | streaming | complete
  const [wsLogs, setWsLogs] = useState([])          // 实时日志
  const [currentNode, setCurrentNode] = useState('') // 当前正在执行的节点
  const wsRef = useRef(null)

  // 加载用户数据
  useEffect(() => {
    setLoading(true)
    getUser(userId)
      .then(res => setUser(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))

    getMatchHistory(userId)
      .then(res => setHistory(res.data.records || []))
      .catch(() => {})
  }, [userId])

  // 清理 WebSocket 连接
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  // 通过 WebSocket 触发匹配
  const handleMatch = useCallback(() => {
    setMatchResult(null)
    setWsLogs([])
    setCurrentNode('')
    setWsStatus('connecting')
    setActiveTab('match')

    // 构建 WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/match/ws/${userId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setWsStatus('streaming')
      setWsLogs(prev => [...prev, { emoji: '🔗', text: 'WebSocket 连接已建立' }])
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'start':
          setWsLogs(prev => [...prev, { emoji: '🚀', text: data.message }])
          break

        case 'node_start':
          setCurrentNode(data.node)
          setWsLogs(prev => [...prev, {
            emoji: data.emoji,
            text: `${data.label}：${data.message}`,
            active: true,
          }])
          break

        case 'node_end':
          // 把最后一条 active 日志标记为完成
          setWsLogs(prev => {
            const updated = [...prev]
            const lastActive = updated.findIndex(l => l.active)
            if (lastActive >= 0) {
              updated[lastActive] = { ...updated[lastActive], active: false, done: true }
            }
            return updated
          })
          setCurrentNode('')
          break

        case 'complete':
          setWsStatus('complete')
          setMatchResult(data.result)
          setActiveTab('letter')
          setWsLogs(prev => [...prev, { emoji: '✅', text: '匹配完成！', done: true }])
          // 刷新历史
          getMatchHistory(userId)
            .then(res => setHistory(res.data.records || []))
            .catch(() => {})
          break

        case 'error':
          setWsStatus('idle')
          setError(data.message)
          setWsLogs(prev => [...prev, { emoji: '❌', text: data.message, error: true }])
          break
      }
    }

    ws.onerror = () => {
      setWsStatus('idle')
      setError('WebSocket 连接失败，请刷新页面重试')
    }

    ws.onclose = (e) => {
      if (e.code !== 1000 && e.code !== 1005) {
        setWsStatus('idle')
      }
    }
  }, [userId])

  const isMatching = wsStatus === 'connecting' || wsStatus === 'streaming'

  if (loading) {
    return (
      <div className="text-center py-20">
        <div className="text-4xl animate-heartbeat inline-block mb-4">💕</div>
        <p className="text-gray-400">加载中...</p>
      </div>
    )
  }

  if (error && !user) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400">{error}</p>
        <Link to="/" className="text-rose-500 hover:underline mt-4 inline-block">← 返回首页</Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* 返回按钮 */}
      <Link to="/" className="text-rose-400 hover:text-rose-600 text-sm mb-6 inline-block no-underline">
        ← 返回发现页
      </Link>

      {/* 用户资料卡 */}
      <div className="bg-white rounded-2xl shadow-sm border border-rose-100/50 overflow-hidden mb-6 animate-fade-in-up">
        <div className={`h-32 bg-gradient-to-br ${user.gender === 'female' ? 'from-pink-400 to-rose-400' : 'from-blue-400 to-indigo-400'} relative`}>
          <div className="absolute -bottom-10 left-8 w-20 h-20 rounded-full bg-white shadow-lg flex items-center justify-center text-3xl font-bold border-4 border-white">
            {user.nickname?.charAt(0)}
          </div>
        </div>

        <div className="pt-14 pb-6 px-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                {user.nickname}
                <span className={`ml-2 text-lg ${user.gender === 'female' ? 'text-pink-400' : 'text-blue-400'}`}>
                  {user.gender === 'female' ? '♀' : '♂'}
                </span>
              </h1>
              <p className="text-gray-500 mt-1">
                {user.age}岁 · {user.city} · {user.education} · {user.mbti}
              </p>
            </div>
            <button
              onClick={handleMatch}
              disabled={isMatching}
              className="px-6 py-3 bg-gradient-to-r from-rose-500 to-pink-500 text-white rounded-full font-medium shadow-lg shadow-rose-200 hover:shadow-xl btn-press disabled:opacity-60 disabled:cursor-not-allowed transition-all"
            >
              {isMatching ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin-slow inline-block">💫</span>
                  AI 匹配中...
                </span>
              ) : (
                '💕 寻找缘分'
              )}
            </button>
          </div>

          {/* 详细信息 */}
          <div className="grid grid-cols-2 gap-4 mt-6">
            <InfoBlock label="关于我" text={user.about_me} />
            <InfoBlock label="理想的Ta" text={user.ideal_partner} />
            <InfoBlock label="兴趣爱好" text={user.hobbies} />
            <InfoBlock label="择偶要求" text={`${user.target_gender === 'female' ? '女生' : '男生'}，${user.target_age_min}-${user.target_age_max}岁，${user.target_city}`} />
          </div>
        </div>
      </div>

      {/* ====== WebSocket 实时进度面板 ====== */}
      {isMatching && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-rose-100/50 animate-fade-in-up mb-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl animate-heartbeat">💕</span>
            <div>
              <p className="text-gray-800 font-medium">AI 红娘正在为你寻找缘分</p>
              <p className="text-gray-400 text-xs">通过 WebSocket 实时推送进度</p>
            </div>
          </div>

          {/* 进度条 */}
          <div className="w-full h-2 bg-rose-50 rounded-full mb-4 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-rose-400 to-pink-400 rounded-full transition-all duration-700 ease-out"
              style={{
                width: currentNode === 'parse_intent' ? '15%'
                     : currentNode === 'hybrid_search' ? '35%'
                     : currentNode === 'post_analysis' ? '55%'
                     : currentNode === 'reflection' ? '70%'
                     : currentNode === 'generate_match' ? '90%'
                     : '8%'
              }}
            />
          </div>

          {/* 实时日志 */}
          <div className="space-y-2">
            {wsLogs.map((log, i) => (
              <div
                key={i}
                className={`flex items-start gap-2 text-sm py-1.5 px-3 rounded-lg transition-all ${
                  log.active ? 'bg-rose-50 text-rose-600' :
                  log.error ? 'bg-red-50 text-red-500' :
                  log.done ? 'text-gray-600' :
                  'text-gray-500'
                }`}
              >
                <span className="flex-shrink-0">{log.emoji}</span>
                <span className={log.active ? 'animate-pulse' : ''}>{log.text}</span>
                {log.active && <span className="ml-auto text-xs text-rose-400">执行中...</span>}
                {log.done && !log.error && <span className="ml-auto text-xs text-green-500">✓</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ====== 匹配结果区域 ====== */}
      {matchResult && !isMatching && (
        <div className="animate-fade-in-up">
          {/* Tab 切换 */}
          <div className="flex gap-2 mb-4">
            <TabBtn active={activeTab === 'match'} onClick={() => setActiveTab('match')}>
              📊 匹配评分
            </TabBtn>
            <TabBtn active={activeTab === 'letter'} onClick={() => setActiveTab('letter')}>
              💌 推荐信 ({matchResult.match_letters?.length || 0})
            </TabBtn>
          </div>

          {/* 评分卡 */}
          {activeTab === 'match' && (
            <div className="space-y-4">
              {matchResult.candidates?.map((cand, i) => (
                <div key={i} className="bg-white rounded-2xl p-6 shadow-sm border border-rose-100/50">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${cand.score >= 80 ? 'bg-gradient-to-br from-rose-400 to-pink-400' : 'bg-gray-300'}`}>
                        {i + 1}
                      </div>
                      <h3 className="text-lg font-bold text-gray-800">{cand.nickname}</h3>
                    </div>
                    <div className={`text-2xl font-bold ${cand.score >= 80 ? 'text-rose-500' : cand.score >= 60 ? 'text-amber-500' : 'text-gray-400'}`}>
                      {cand.score}<span className="text-sm">分</span>
                    </div>
                  </div>
                  <div className="w-full h-2 bg-rose-100 rounded-full mb-3">
                    <div
                      className="h-full bg-gradient-to-r from-rose-400 to-pink-400 rounded-full transition-all duration-500"
                      style={{ width: `${cand.score}%` }}
                    />
                  </div>
                  <p className="text-gray-600 text-sm leading-relaxed">{cand.reason}</p>
                  <Link
                    to={`/user/${cand.user_id}`}
                    className="text-rose-400 text-sm hover:underline mt-2 inline-block"
                  >
                    查看 Ta 的资料 →
                  </Link>
                </div>
              ))}
            </div>
          )}

          {/* 推荐信 */}
          {activeTab === 'letter' && (
            <div className="space-y-6">
              {matchResult.match_letters?.map((letter, i) => (
                <div key={i} className="bg-gradient-to-br from-rose-50 to-pink-50 rounded-2xl p-8 border border-rose-200/50 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-xl">💌</span>
                    <h3 className="font-bold text-rose-600">
                      缘分推荐信 - {matchResult.candidates?.[i]?.nickname || ''}
                    </h3>
                  </div>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{letter}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 历史匹配记录 */}
      {!isMatching && !matchResult && history.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-bold text-gray-700 mb-4">📋 近期匹配记录</h3>
          <div className="space-y-3">
            {history.slice(0, 3).map((record, i) => (
              <div key={i} className="bg-white rounded-xl p-4 shadow-sm border border-rose-100/50 flex items-center justify-between">
                <div>
                  <span className="text-sm text-gray-500">{record.created_at?.slice(0, 16).replace('T', ' ')}</span>
                  <span className="ml-3 text-sm font-medium text-gray-700">
                    {record.candidates?.length || 0} 位推荐
                  </span>
                </div>
                <span className="text-rose-500 font-bold">
                  最高 {Math.max(...(record.candidates?.map(c => c.score) || [0]))} 分
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ===== 辅助子组件 =====

function InfoBlock({ label, text }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <p className="text-xs text-rose-400 font-medium mb-1">{label}</p>
      <p className="text-sm text-gray-700 leading-relaxed">{text || '-'}</p>
    </div>
  )
}

function TabBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
        active
          ? 'bg-rose-500 text-white shadow-md'
          : 'bg-white text-gray-600 border border-rose-200 hover:bg-rose-50'
      }`}
    >
      {children}
    </button>
  )
}
