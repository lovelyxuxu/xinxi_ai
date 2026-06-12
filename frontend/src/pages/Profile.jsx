/**
 * 心犀AI - 个人中心（私人空间）
 * ================================
 * 综合个人中心，包含三大功能模块：
 * 1. 个人主页：查看和编辑个人资料
 * 2. 匹配记录：历史匹配结果和推荐信
 * 3. AI 访谈：与 AI 红娘聊天，完善个人画像
 *
 * 学习要点：
 * - Tab 切换：用 useState 管理当前活跃 tab
 * - WebSocket 聊天：连接访谈子图（Phase 5），实时多轮对话
 * - 条件渲染：根据当前 tab 展示不同内容区域
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { getUser, getMatchHistory } from '../api/client'

export default function Profile() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('profile')

  // 匹配历史
  const [history, setHistory] = useState([])
  const [selectedMatch, setSelectedMatch] = useState(null)

  // AI 访谈
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatStatus, setChatStatus] = useState('idle') // idle | connecting | chatting | complete
  const chatStatusRef = useRef('idle')
  const wsRef = useRef(null)
  const chatEndRef = useRef(null)

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

  // 自动滚动到最新消息
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // 同步 chatStatusRef
  useEffect(() => {
    chatStatusRef.current = chatStatus
  }, [chatStatus])

  // 清理 WebSocket
  useEffect(() => {
    return () => { if (wsRef.current) wsRef.current.close() }
  }, [])

  // AI 访谈：开始聊天
  const startInterview = useCallback(() => {
    setChatMessages([])
    setChatStatus('connecting')

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/interview/ws/${userId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setChatStatus('chatting')
      setChatMessages(prev => [...prev, { role: 'system', text: '连接已建立，AI 红娘正在准备...' }])
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'ai_message') {
        setChatMessages(prev => [...prev, {
          role: 'ai',
          text: data.message,
          isComplete: data.is_complete || false,
        }])
      } else if (data.type === 'system') {
        setChatMessages(prev => [...prev, { role: 'system', text: data.message }])
      } else if (data.type === 'error') {
        setChatMessages(prev => [...prev, { role: 'error', text: data.message }])
        setChatStatus('idle')
      }
    }

    ws.onerror = () => {
      setChatStatus('idle')
      setChatMessages(prev => [...prev, { role: 'error', text: 'WebSocket 连接失败' }])
    }

    ws.onclose = () => {
      if (chatStatusRef.current !== 'complete') setChatStatus('idle')
    }
  }, [userId])

  // AI 访谈：发送消息
  const sendChatMessage = useCallback(() => {
    if (!chatInput.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    const msg = chatInput.trim()
    setChatMessages(prev => [...prev, { role: 'user', text: msg }])
    wsRef.current.send(msg)
    setChatInput('')
  }, [chatInput])

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
    <div className="max-w-4xl mx-auto">
      {/* 顶部用户概览 */}
      <div className="bg-gradient-to-r from-rose-500 to-pink-500 rounded-2xl p-6 mb-6 text-white shadow-lg animate-fade-in-up">
        <div className="flex items-center gap-5">
          <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur flex items-center justify-center text-4xl font-bold border-2 border-white/40">
            {user.nickname?.charAt(0)}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">
              {user.nickname}
              <span className="ml-2 text-lg opacity-80">
                {user.gender === 'female' ? '♀' : '♂'}
              </span>
            </h1>
            <p className="text-white/80 mt-1">
              {user.age}岁 · {user.city} · {user.education} · {user.mbti}
            </p>
            <p className="text-white/60 text-sm mt-1">
              {user.annual_income} · {user.marital_status}
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{history.length}</div>
            <div className="text-white/60 text-sm">次匹配</div>
          </div>
        </div>
      </div>

      {/* Tab 切换栏 */}
      <div className="flex gap-2 mb-6">
        <TabBtn active={activeTab === 'profile'} onClick={() => setActiveTab('profile')}>
          👤 个人主页
        </TabBtn>
        <TabBtn active={activeTab === 'history'} onClick={() => setActiveTab('history')}>
          📋 匹配记录 ({history.length})
        </TabBtn>
        <TabBtn active={activeTab === 'interview'} onClick={() => setActiveTab('interview')}>
          💬 AI 访谈
        </TabBtn>
      </div>

      {/* ====== 个人主页 Tab ====== */}
      {activeTab === 'profile' && (
        <div className="space-y-4 animate-fade-in-up">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-rose-100/50">
            <h2 className="text-lg font-bold text-gray-800 mb-4">📝 关于我</h2>
            <div className="grid grid-cols-2 gap-4">
              <InfoBlock label="关于我" text={user.about_me} />
              <InfoBlock label="理想的Ta" text={user.ideal_partner} />
              <InfoBlock label="兴趣爱好" text={user.hobbies} />
              <InfoBlock label="择偶要求" text={`${user.target_gender === 'female' ? '女生' : '男生'}，${user.target_age_min}-${user.target_age_max}岁，${user.target_city}`} />
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm border border-rose-100/50">
            <h2 className="text-lg font-bold text-gray-800 mb-4">📊 详细信息</h2>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <DetailItem label="省份" value={user.province} />
              <DetailItem label="学历" value={user.education} />
              <DetailItem label="年收入" value={user.annual_income} />
              <DetailItem label="婚姻状况" value={user.marital_status} />
              <DetailItem label="MBTI" value={user.mbti} />
              <DetailItem label="用户ID" value={user.user_id} />
            </div>
          </div>

          <div className="flex gap-3">
            <Link
              to={`/user/${userId}`}
              className="flex-1 text-center py-3 bg-gradient-to-r from-rose-500 to-pink-500 text-white rounded-full font-medium shadow-lg hover:shadow-xl transition-all"
            >
              💕 去寻找缘分
            </Link>
            <button
              onClick={startInterview}
              className="flex-1 py-3 bg-white text-rose-500 rounded-full font-medium border-2 border-rose-300 hover:bg-rose-50 transition-all"
            >
              💬 与 AI 红娘聊天
            </button>
          </div>
        </div>
      )}

      {/* ====== 匹配记录 Tab ====== */}
      {activeTab === 'history' && (
        <div className="space-y-4 animate-fade-in-up">
          {history.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <div className="text-5xl mb-4">📭</div>
              <p>还没有匹配记录</p>
              <Link to={`/user/${userId}`} className="text-rose-500 hover:underline mt-2 inline-block">
                去寻找缘分 →
              </Link>
            </div>
          ) : (
            <>
              {/* 匹配列表 */}
              <div className="space-y-3">
                {history.map((record, i) => (
                  <div
                    key={i}
                    className="bg-white rounded-xl p-4 shadow-sm border border-rose-100/50 cursor-pointer hover:shadow-md transition-all"
                    onClick={() => setSelectedMatch(selectedMatch === i ? null : i)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-sm text-gray-500">
                          {record.created_at?.slice(0, 16).replace('T', ' ')}
                        </span>
                        <span className="ml-3 text-sm font-medium text-gray-700">
                          {record.candidates?.length || 0} 位推荐
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-rose-500 font-bold">
                          最高 {Math.max(...(record.candidates?.map(c => c.score) || [0]))} 分
                        </span>
                        <span className="text-gray-300">{selectedMatch === i ? '▲' : '▼'}</span>
                      </div>
                    </div>

                    {/* 展开详情 */}
                    {selectedMatch === i && (
                      <div className="mt-4 pt-4 border-t border-rose-100 space-y-3">
                        {record.candidates?.map((cand, j) => (
                          <div key={j} className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold ${cand.score >= 80 ? 'bg-rose-400' : 'bg-gray-300'}`}>
                              {j + 1}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-gray-800">{cand.nickname}</span>
                                <span className={`text-sm font-bold ${cand.score >= 80 ? 'text-rose-500' : 'text-gray-400'}`}>
                                  {cand.score}分
                                </span>
                              </div>
                              <p className="text-xs text-gray-500 mt-0.5">{cand.reason}</p>
                            </div>
                          </div>
                        ))}
                        {record.match_letters?.length > 0 && (
                          <div className="mt-3 bg-rose-50 rounded-xl p-4">
                            <p className="text-sm font-medium text-rose-600 mb-2">💌 推荐信</p>
                            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                              {record.match_letters[0]}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ====== AI 访谈 Tab ====== */}
      {activeTab === 'interview' && (
        <div className="animate-fade-in-up">
          <div className="bg-white rounded-2xl shadow-sm border border-rose-100/50 overflow-hidden">
            {/* 聊天头部 */}
            <div className="bg-gradient-to-r from-rose-400 to-pink-400 p-4 text-white">
              <div className="flex items-center gap-3">
                <span className="text-2xl">💕</span>
                <div>
                  <p className="font-bold">AI 红娘访谈</p>
                  <p className="text-white/70 text-xs">
                    {chatStatus === 'idle' ? '点击开始聊天' :
                     chatStatus === 'connecting' ? '连接中...' :
                     chatStatus === 'chatting' ? '对话进行中' : '访谈完成'}
                  </p>
                </div>
                {chatStatus === 'idle' && (
                  <button
                    onClick={startInterview}
                    className="ml-auto px-4 py-1.5 bg-white/20 rounded-full text-sm font-medium hover:bg-white/30 transition-all"
                  >
                    开始访谈
                  </button>
                )}
              </div>
            </div>

            {/* 聊天消息区 */}
            <div className="h-96 overflow-y-auto p-4 space-y-3 bg-gray-50">
              {chatMessages.length === 0 && chatStatus === 'idle' && (
                <div className="text-center py-12 text-gray-400">
                  <div className="text-4xl mb-3">🌸</div>
                  <p className="text-sm">点击上方"开始访谈"按钮</p>
                  <p className="text-xs mt-1">AI 红娘会通过聊天帮你完善个人画像</p>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-rose-500 text-white rounded-br-md'
                      : msg.role === 'error'
                      ? 'bg-red-100 text-red-600 rounded-bl-md'
                      : msg.role === 'system'
                      ? 'bg-gray-200 text-gray-500 rounded-bl-md text-xs'
                      : 'bg-white text-gray-800 rounded-bl-md shadow-sm border border-rose-100/50'
                  }`}>
                    {msg.role === 'ai' && <span className="text-rose-400 text-xs font-medium">AI 红娘</span>}
                    <p className={msg.role === 'ai' ? 'mt-1' : ''}>{msg.text}</p>
                    {msg.isComplete && (
                      <p className="text-xs text-green-500 mt-2 font-medium">✅ 画像已完善</p>
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* 输入区 */}
            {(chatStatus === 'chatting') && (
              <div className="p-4 border-t border-rose-100 bg-white">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendChatMessage())}
                    placeholder="输入你的回复..."
                    className="flex-1 px-4 py-2.5 rounded-full border border-rose-200 focus:outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100 text-sm"
                  />
                  <button
                    onClick={sendChatMessage}
                    disabled={!chatInput.trim()}
                    className="px-5 py-2.5 bg-rose-500 text-white rounded-full text-sm font-medium hover:bg-rose-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                  >
                    发送
                  </button>
                </div>
              </div>
            )}
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

function DetailItem({ label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg px-3 py-2">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm text-gray-700 font-medium">{value || '-'}</p>
    </div>
  )
}

function TabBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all ${
        active
          ? 'bg-rose-500 text-white shadow-md shadow-rose-200'
          : 'bg-white text-gray-600 border border-rose-200 hover:bg-rose-50'
      }`}
    >
      {children}
    </button>
  )
}
