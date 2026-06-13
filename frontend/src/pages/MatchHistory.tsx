/**
 * 心犀AI - 匹配历史页（shadcn/ui 版）
 * =======================================
 *
 * 【shadcn/ui 改进点】
 * - Select 替代原生 <select>（用户选择器）
 * - Collapsible 替代 <details>（Agent 日志折叠）
 * - Card + Badge 统一展示
 * - LoadingState + ErrorAlert 共享组件
 */
import { useState, useEffect } from 'react'
import { getUsers, getMatchHistory } from '../api/client'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { LoadingState } from '@/components/LoadingState'
import { ScoreDisplay } from '@/components/ScoreDisplay'
import { MatchLetterCard } from '@/components/MatchLetterCard'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { UserPublic, MatchResult } from '@/types'

export default function MatchHistory() {
  const [users, setUsers] = useState<UserPublic[]>([])
  const [selectedUser, setSelectedUser] = useState('')
  const [records, setRecords] = useState<MatchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedLetter, setExpandedLetter] = useState<string | null>(null)
  const [expandedLog, setExpandedLog] = useState<string | null>(null)

  useEffect(() => {
    getUsers(1, 100).then(res => setUsers(res.data.users || [])).catch(() => {})
  }, [])

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
        <h1 className="text-3xl font-bold text-foreground mb-2">📋 匹配历史</h1>
        <p className="text-muted-foreground">选择用户查看 AI 匹配记录和推荐信</p>
      </div>

      {/* 用户选择器 */}
      <Card className="mb-6 border-border/50">
        <CardContent className="p-6">
          <label className="block text-sm text-muted-foreground mb-2">选择用户</label>
          <Select value={selectedUser} onValueChange={setSelectedUser}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="-- 请选择 --" />
            </SelectTrigger>
            <SelectContent>
              {users.map(u => (
                <SelectItem key={u.user_id} value={u.user_id}>
                  {u.nickname} ({u.gender === 'female' ? '♀' : '♂'} {u.age}岁 {u.city})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {loading && <LoadingState variant="page" />}

      {!loading && selectedUser && records.length === 0 && (
        <Card className="border-border/50">
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">暂无匹配记录</p>
            <Button asChild className="mt-4 rounded-full bg-rose-500 hover:bg-rose-600">
              <Link to={`/user/${selectedUser}`}>去发起匹配 →</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {!loading && records.length > 0 && (
        <div className="space-y-6">
          {records.map((record, ri) => (
            <Card key={ri} className="border-border/50 overflow-hidden animate-fade-in-up">
              {/* 记录头部 */}
              <div className="px-6 py-4 bg-gradient-to-r from-rose-50 to-pink-50 border-b border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm text-muted-foreground">{record.created_at?.slice(0, 16).replace('T', ' ')}</span>
                    <Badge variant="secondary" className="ml-3">{record.candidates?.length || 0} 位推荐</Badge>
                  </div>
                  <span className="text-lg font-bold text-primary">
                    最高 {Math.max(...(record.candidates?.map(c => c.score) || [0]))} 分
                  </span>
                </div>
              </div>

              {/* 候选人列表 */}
              <CardContent className="p-6 space-y-4">
                {record.candidates?.map((cand, ci) => {
                  const letterKey = `${ri}-${ci}`
                  const isExpanded = expandedLetter === letterKey
                  const letter = record.match_letters?.[ci]
                  return (
                    <div key={ci} className="border border-border rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <Link to={`/user/${cand.user_id}`} className="text-primary hover:underline font-medium">{cand.nickname}</Link>
                          <ScoreDisplay score={cand.score} variant="badge" />
                        </div>
                        {letter && (
                          <Button variant="ghost" size="sm" onClick={() => setExpandedLetter(isExpanded ? null : letterKey)} className="text-pink-400">
                            {isExpanded ? '收起信件 ▲' : '💌 查看推荐信'}
                          </Button>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{cand.reason}</p>
                      {isExpanded && letter && <div className="mt-3"><MatchLetterCard letter={letter} candidateName={cand.nickname} /></div>}
                    </div>
                  )
                })}
              </CardContent>

              {/* Agent 日志 — Collapsible */}
              {record.agent_log && record.agent_log.length > 0 && (
                <Collapsible open={expandedLog === `${ri}`} onOpenChange={(open) => setExpandedLog(open ? `${ri}` : null)}>
                  <div className="px-6 pb-4">
                    <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-gray-600 cursor-pointer">
                      🤖 Agent 执行日志 ({record.agent_log.length} 条)
                      {expandedLog === `${ri}` ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="mt-2 bg-muted rounded-lg p-3 text-xs text-muted-foreground font-mono space-y-1 max-h-48 overflow-y-auto">
                        {record.agent_log.map((log, li) => <div key={li}>{log}</div>)}
                      </div>
                    </CollapsibleContent>
                  </div>
                </Collapsible>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
