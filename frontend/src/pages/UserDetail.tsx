/**
 * 心犀AI - 用户详情页 + WebSocket 实时匹配（shadcn/ui 版）
 * ==========================================================
 *
 * 【shadcn/ui 改进点】
 * - Tabs 组件替代手写的 TabBtn（带键盘导航 + 动画指示器）
 * - Progress 组件替代手写进度条（内置动画）
 * - Button 组件统一按钮样式
 * - Skeleton 骨架屏替代心跳 emoji 加载态
 * - 使用 InfoBlock、UserAvatar、ScoreDisplay、MatchLetterCard、MatchProgressPanel 共享组件
 *
 * 【学习要点 — Tabs 组件】
 * shadcn 的 Tabs 基于 Radix UI，结构是：
 * <Tabs value={tab} onValueChange={setTab}>  — 状态管理
 *   <TabsList>                                — 标签按钮容器
 *     <TabsTrigger value="a">Tab A</TabsTrigger>
 *   </TabsList>
 *   <TabsContent value="a">Content A</TabsContent>
 * </Tabs>
 *
 * 和手写 TabBtn 的区别：
 * - 内置键盘导航（← → 切换 tab）
 * - 支持 aria 无障碍标签
 * - 自动管理显示/隐藏逻辑
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getUser, getMatchHistory } from '../api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { InfoBlock } from '@/components/InfoBlock'
import { UserAvatar } from '@/components/UserAvatar'
import { ScoreDisplay } from '@/components/ScoreDisplay'
import { MatchLetterCard } from '@/components/MatchLetterCard'
import { MatchProgressPanel } from '@/components/MatchProgressPanel'
import { LoadingState } from '@/components/LoadingState'
import { ErrorAlert } from '@/components/ErrorAlert'
import { cn } from '@/lib/utils'
import type { UserProfile, MatchResult, MatchWsStatus, WsLogEntry, WsMatchEvent } from '@/types'

export default function UserDetail() {
  const { userId } = useParams<{ userId: string }>()
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null)
  const [history, setHistory] = useState<MatchResult[]>([])
  const [activeTab, setActiveTab] = useState('profile')
  const [error, setError] = useState<string | null>(null)

  // WebSocket 状态
  const [wsStatus, setWsStatus] = useState<MatchWsStatus>('idle')
  const [wsLogs, setWsLogs] = useState<WsLogEntry[]>([])
  const [currentNode, setCurrentNode] = useState('')
  const wsRef = useRef<WebSocket | null>(null)

  const isMatching = wsStatus === 'connecting' || wsStatus === 'streaming'

  // 加载用户 + 历史
  useEffect(() => {
    if (!userId) return
    setLoading(true)
    getUser(userId)
      .then(res => setUser(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
    getMatchHistory(userId)
      .then(res => setHistory(res.data.records || []))
      .catch(() => {})
  }, [userId])

  // 清理 WebSocket
  useEffect(() => {
    return () => { wsRef.current?.close() }
  }, [])

  // WebSocket 匹配处理
  const handleMatch = useCallback(() => {
    setMatchResult(null)
    setWsLogs([])
    setCurrentNode('')
    setWsStatus('connecting')
    setActiveTab('match')

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/match/ws/${userId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setWsStatus('streaming')
      setWsLogs(prev => [...prev, { emoji: '🔗', text: 'WebSocket 连接已建立' }])
    }

    ws.onmessage = (event) => {
      const data: WsMatchEvent = JSON.parse(event.data)
      switch (data.type) {
        case 'start':
          setWsLogs(prev => [...prev, { emoji: '🚀', text: data.message }])
          break
        case 'node_start':
          setCurrentNode(data.node)
          setWsLogs(prev => [...prev, { emoji: data.emoji, text: `${data.label}：${data.message}`, active: true }])
          break
        case 'node_end':
          setWsLogs(prev => {
            const u = [...prev]; const i = u.findIndex(l => l.active)
            if (i >= 0) u[i] = { ...u[i], active: false, done: true }
            return u
          })
          setCurrentNode('')
          break
        case 'complete':
          setWsStatus('complete')
          setMatchResult(data.result)
          setActiveTab('letter')
          setWsLogs(prev => [...prev, { emoji: '✅', text: '匹配完成！', done: true }])
          if (userId) getMatchHistory(userId).then(res => setHistory(res.data.records || [])).catch(() => {})
          break
        case 'error':
          setWsStatus('idle')
          setError(data.message)
          setWsLogs(prev => [...prev, { emoji: '❌', text: data.message, error: true }])
          break
      }
    }

    ws.onerror = () => { setWsStatus('idle'); setError('WebSocket 连接失败') }
    ws.onclose = (e) => { if (e.code !== 1000 && e.code !== 1005) setWsStatus('idle') }
  }, [userId])

  if (loading) return <LoadingState variant="page" />
  if (error && !user) return <ErrorAlert message={error} hint="请返回首页重试" />
  if (!user) return null

  return (
    <div className="max-w-3xl mx-auto">
      <Link to="/" className="text-rose-400 hover:text-rose-600 text-sm mb-6 inline-block no-underline">← 返回发现页</Link>

      {/* 用户资料卡 */}
      <Card className="overflow-hidden mb-6 animate-fade-in-up border-border/50">
        <div className={cn("h-32 bg-gradient-to-br relative", user.gender === 'female' ? 'from-pink-400 to-rose-400' : 'from-blue-400 to-indigo-400')}>
          <div className="absolute -bottom-10 left-8">
            <UserAvatar nickname={user.nickname} gender={user.gender} size="lg" className="border-4 border-white" />
          </div>
        </div>
        <CardContent className="pt-14 pb-6 px-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                {user.nickname}
                <span className={cn("ml-2 text-lg", user.gender === 'female' ? 'text-pink-400' : 'text-blue-400')}>
                  {user.gender === 'female' ? '♀' : '♂'}
                </span>
              </h1>
              <p className="text-muted-foreground mt-1">{user.age}岁 · {user.city} · {user.education} · {user.mbti}</p>
            </div>
            <Button
              onClick={handleMatch}
              disabled={isMatching}
              className="bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-600 hover:to-pink-600 shadow-lg shadow-rose-200 rounded-full px-6"
            >
              {isMatching ? (<><span className="animate-spin-slow mr-2">💫</span>AI 匹配中...</>) : '💕 寻找缘分'}
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-6">
            <InfoBlock label="关于我" text={user.about_me} />
            <InfoBlock label="理想的Ta" text={user.ideal_partner} />
            <InfoBlock label="兴趣爱好" text={user.hobbies} />
            <InfoBlock label="择偶要求" text={`${user.target_gender === 'female' ? '女生' : '男生'}，${user.target_age_min}-${user.target_age_max}岁，${user.target_city}`} />
          </div>
        </CardContent>
      </Card>

      {/* WebSocket 实时进度面板 — 使用共享组件 */}
      {isMatching && <MatchProgressPanel currentNode={currentNode} logs={wsLogs} />}

      {/* 匹配结果 */}
      {matchResult && !isMatching && (
        <div className="animate-fade-in-up mt-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="match">📊 匹配评分</TabsTrigger>
              <TabsTrigger value="letter">💌 推荐信 ({matchResult.match_letters?.length || 0})</TabsTrigger>
            </TabsList>

            {/* 评分卡 */}
            <TabsContent value="match" className="space-y-4">
              {matchResult.candidates?.map((cand, i) => (
                <Card key={i} className="border-border/50">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={cn("w-10 h-10 rounded-full flex items-center justify-center text-white font-bold", cand.score >= 80 ? "bg-gradient-to-br from-rose-400 to-pink-400" : "bg-gray-300")}>
                          {i + 1}
                        </div>
                        <h3 className="text-lg font-bold text-foreground">{cand.nickname}</h3>
                      </div>
                      <ScoreDisplay score={cand.score} variant="large" />
                    </div>
                    <ScoreDisplay score={cand.score} variant="progress" className="mb-3" />
                    <p className="text-gray-600 text-sm leading-relaxed">{cand.reason}</p>
                    <Link to={`/user/${cand.user_id}`} className="text-rose-400 text-sm hover:underline mt-2 inline-block">查看 Ta 的资料 →</Link>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>

            {/* 推荐信 */}
            <TabsContent value="letter" className="space-y-6">
              {matchResult.match_letters?.map((letter, i) => (
                <MatchLetterCard key={i} letter={letter} candidateName={matchResult.candidates?.[i]?.nickname} />
              ))}
            </TabsContent>
          </Tabs>
        </div>
      )}

      {/* 历史匹配记录 */}
      {!isMatching && !matchResult && history.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-bold text-gray-700 mb-4">📋 近期匹配记录</h3>
          <div className="space-y-3">
            {history.slice(0, 3).map((record, i) => (
              <Card key={i} className="border-border/50">
                <CardContent className="p-4 flex items-center justify-between">
                  <div>
                    <span className="text-sm text-muted-foreground">{record.created_at?.slice(0, 16).replace('T', ' ')}</span>
                    <span className="ml-3 text-sm font-medium text-gray-700">{record.candidates?.length || 0} 位推荐</span>
                  </div>
                  <span className="text-primary font-bold">最高 {Math.max(...(record.candidates?.map(c => c.score) || [0]))} 分</span>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
