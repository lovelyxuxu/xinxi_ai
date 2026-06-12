/**
 * 心犀AI - 个人中心（shadcn/ui 版）
 * =====================================
 *
 * 【shadcn/ui 改进点】
 * - Tabs 替代手写 TabBtn（统一风格 + 无障碍支持）
 * - ScrollArea 替代 overflow-y-auto（平滑滚动 + 自定义滚动条）
 * - Card 统一卡片容器样式
 * - 使用 InfoBlock、DetailItem、UserAvatar 共享组件
 *
 * 【学习要点 — ScrollArea 组件】
 * shadcn 的 ScrollArea 基于 Radix UI：
 * - 自定义滚动条样式（不再是浏览器默认丑丑的滚动条）
 * - 平滑滚动
 * - 可以控制滚动条的显示/隐藏行为
 * - 在聊天场景特别有用：消息列表需要优雅地滚动
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getUser, getMatchHistory } from '../api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { InfoBlock } from '@/components/InfoBlock'
import { DetailItem } from '@/components/DetailItem'
import { UserAvatar } from '@/components/UserAvatar'
import { LoadingState } from '@/components/LoadingState'
import { ErrorAlert } from '@/components/ErrorAlert'
import { cn } from '@/lib/utils'
import type { UserProfile, MatchResult, ChatStatus, ChatMessage, WsInterviewEvent } from '@/types'

export default function Profile() {
  const { userId } = useParams<{ userId: string }>()
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('profile')

  const [history, setHistory] = useState<MatchResult[]>([])
  const [selectedMatch, setSelectedMatch] = useState<number | null>(null)

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatStatus, setChatStatus] = useState<ChatStatus>('idle')

  const chatStatusRef = useRef<ChatStatus>('idle')
  const wsRef = useRef<WebSocket | null>(null)
  const chatEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!userId) return
    setLoading(true)
    getUser(userId).then(res => setUser(res.data)).catch(err => setError(err.message)).finally(() => setLoading(false))
    getMatchHistory(userId).then(res => setHistory(res.data.records || [])).catch(() => {})
  }, [userId])

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatMessages])
  useEffect(() => { chatStatusRef.current = chatStatus }, [chatStatus])
  useEffect(() => { return () => { wsRef.current?.close() } }, [])

  const startInterview = useCallback(() => {
    setChatMessages([])
    setChatStatus('connecting')
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/interview/ws/${userId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setChatStatus('chatting')
      setChatMessages(prev => [...prev, { role: 'system', text: '连接已建立，AI 红娘正在准备...' }])
    }
    ws.onmessage = (event) => {
      const data: WsInterviewEvent = JSON.parse(event.data)
      if (data.type === 'ai_message') {
        setChatMessages(prev => [...prev, { role: 'ai', text: data.message, isComplete: data.is_complete || false }])
      } else if (data.type === 'system') {
        setChatMessages(prev => [...prev, { role: 'system', text: data.message }])
      } else if (data.type === 'error') {
        setChatMessages(prev => [...prev, { role: 'error', text: data.message }])
        setChatStatus('idle')
      }
    }
    ws.onerror = () => { setChatStatus('idle'); setChatMessages(prev => [...prev, { role: 'error', text: 'WebSocket 连接失败' }]) }
    ws.onclose = () => { if (chatStatusRef.current !== 'complete') setChatStatus('idle') }
  }, [userId])

  const sendChatMessage = useCallback(() => {
    if (!chatInput.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setChatMessages(prev => [...prev, { role: 'user', text: chatInput.trim() }])
    wsRef.current.send(chatInput.trim())
    setChatInput('')
  }, [chatInput])

  if (loading) return <LoadingState variant="page" />
  if (error && !user) return <ErrorAlert message={error} />
  if (!user) return null

  return (
    <div className="max-w-4xl mx-auto">
      {/* 用户概览横幅 */}
      <Card className="bg-gradient-to-r from-rose-500 to-pink-500 border-none text-white shadow-lg animate-fade-in-up mb-6">
        <CardContent className="p-6 flex items-center gap-5">
          <UserAvatar nickname={user.nickname} gender={user.gender} size="lg" className="border-2 border-white/40 bg-white/20" />
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{user.nickname} <span className="ml-2 text-lg opacity-80">{user.gender === 'female' ? '♀' : '♂'}</span></h1>
            <p className="text-white/80 mt-1">{user.age}岁 · {user.city} · {user.education} · {user.mbti}</p>
            <p className="text-white/60 text-sm mt-1">{user.annual_income} · {user.marital_status}</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{history.length}</div>
            <div className="text-white/60 text-sm">次匹配</div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs 切换 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="profile">👤 个人主页</TabsTrigger>
          <TabsTrigger value="history">📋 匹配记录 ({history.length})</TabsTrigger>
          <TabsTrigger value="interview">💬 AI 访谈</TabsTrigger>
        </TabsList>

        {/* 个人主页 */}
        <TabsContent value="profile" className="space-y-4 animate-fade-in-up">
          <Card className="border-border/50">
            <CardHeader><CardTitle>📝 关于我</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
              <InfoBlock label="关于我" text={user.about_me} />
              <InfoBlock label="理想的Ta" text={user.ideal_partner} />
              <InfoBlock label="兴趣爱好" text={user.hobbies} />
              <InfoBlock label="择偶要求" text={`${user.target_gender === 'female' ? '女生' : '男生'}，${user.target_age_min}-${user.target_age_max}岁，${user.target_city}`} />
            </CardContent>
          </Card>
          <Card className="border-border/50">
            <CardHeader><CardTitle>📊 详细信息</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-3 gap-4">
              <DetailItem label="省份" value={user.province} />
              <DetailItem label="学历" value={user.education} />
              <DetailItem label="年收入" value={user.annual_income} />
              <DetailItem label="婚姻状况" value={user.marital_status} />
              <DetailItem label="MBTI" value={user.mbti} />
              <DetailItem label="用户ID" value={user.user_id} />
            </CardContent>
          </Card>
          <div className="flex gap-3">
            <Button asChild className="flex-1 bg-gradient-to-r from-rose-500 to-pink-500 rounded-full shadow-lg">
              <Link to={`/user/${userId}`}>💕 去寻找缘分</Link>
            </Button>
            <Button variant="outline" onClick={startInterview} className="flex-1 rounded-full border-2 border-rose-300 text-rose-500">💬 与 AI 红娘聊天</Button>
          </div>
        </TabsContent>

        {/* 匹配记录 */}
        <TabsContent value="history" className="space-y-3 animate-fade-in-up">
          {history.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <div className="text-5xl mb-4">📭</div>
              <p>还没有匹配记录</p>
              <Link to={`/user/${userId}`} className="text-rose-500 hover:underline mt-2 inline-block">去寻找缘分 →</Link>
            </div>
          ) : history.map((record, i) => (
            <Card key={i} className="border-border/50 cursor-pointer hover:shadow-md transition-all" onClick={() => setSelectedMatch(selectedMatch === i ? null : i)}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm text-muted-foreground">{record.created_at?.slice(0, 16).replace('T', ' ')}</span>
                    <span className="ml-3 text-sm font-medium">{record.candidates?.length || 0} 位推荐</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-primary font-bold">最高 {Math.max(...(record.candidates?.map(c => c.score) || [0]))} 分</span>
                    <span className="text-gray-300">{selectedMatch === i ? '▲' : '▼'}</span>
                  </div>
                </div>
                {selectedMatch === i && (
                  <div className="mt-4 pt-4 border-t border-border space-y-3">
                    {record.candidates?.map((cand, j) => (
                      <div key={j} className="flex items-center gap-3">
                        <div className={cn("w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold", cand.score >= 80 ? "bg-rose-400" : "bg-gray-300")}>{j + 1}</div>
                        <div className="flex-1">
                          <span className="font-medium">{cand.nickname}</span>
                          <span className={cn("ml-2 text-sm font-bold", cand.score >= 80 ? "text-rose-500" : "text-gray-400")}>{cand.score}分</span>
                          <p className="text-xs text-muted-foreground mt-0.5">{cand.reason}</p>
                        </div>
                      </div>
                    ))}
                    {record.match_letters?.[0] && (
                      <Card className="bg-rose-50 border-rose-200/50 mt-3">
                        <CardContent className="p-4">
                          <p className="text-sm font-medium text-rose-600 mb-2">💌 推荐信</p>
                          <p className="text-sm text-gray-700 whitespace-pre-wrap">{record.match_letters[0]}</p>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* AI 访谈 */}
        <TabsContent value="interview" className="animate-fade-in-up">
          <Card className="border-border/50 overflow-hidden">
            {/* 聊天头部 */}
            <div className="bg-gradient-to-r from-rose-400 to-pink-400 p-4 text-white">
              <div className="flex items-center gap-3">
                <span className="text-2xl">💕</span>
                <div className="flex-1">
                  <p className="font-bold">AI 红娘访谈</p>
                  <p className="text-white/70 text-xs">
                    {chatStatus === 'idle' ? '点击开始聊天' : chatStatus === 'connecting' ? '连接中...' : chatStatus === 'chatting' ? '对话进行中' : '访谈完成'}
                  </p>
                </div>
                {chatStatus === 'idle' && (
                  <Button onClick={startInterview} variant="secondary" size="sm" className="rounded-full bg-white/20 text-white hover:bg-white/30">开始访谈</Button>
                )}
              </div>
            </div>

            {/* 消息区 — ScrollArea */}
            <ScrollArea className="h-96">
              <div className="p-4 space-y-3">
                {chatMessages.length === 0 && chatStatus === 'idle' && (
                  <div className="text-center py-12 text-muted-foreground">
                    <div className="text-4xl mb-3">🌸</div>
                    <p className="text-sm">点击上方"开始访谈"按钮</p>
                    <p className="text-xs mt-1">AI 红娘会通过聊天帮你完善个人画像</p>
                  </div>
                )}
                {chatMessages.map((msg, i) => (
                  <div key={i} className={cn("flex", msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                    <div className={cn("max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                      msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-br-md' :
                      msg.role === 'error' ? 'bg-red-100 text-red-600 rounded-bl-md' :
                      msg.role === 'system' ? 'bg-muted text-muted-foreground rounded-bl-md text-xs' :
                      'bg-white text-gray-800 rounded-bl-md shadow-sm border border-border/50'
                    )}>
                      {msg.role === 'ai' && <span className="text-rose-400 text-xs font-medium">AI 红娘</span>}
                      <p className={msg.role === 'ai' ? 'mt-1' : ''}>{msg.text}</p>
                      {msg.isComplete && <p className="text-xs text-green-500 mt-2 font-medium">✅ 画像已完善</p>}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
            </ScrollArea>

            {/* 输入区 */}
            {chatStatus === 'chatting' && (
              <div className="p-4 border-t border-border bg-white flex gap-2">
                <Input
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendChatMessage())}
                  placeholder="输入你的回复..."
                  className="rounded-full"
                />
                <Button onClick={sendChatMessage} disabled={!chatInput.trim()} className="rounded-full bg-rose-500 hover:bg-rose-600">发送</Button>
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
