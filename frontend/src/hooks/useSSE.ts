/**
 * useSSE - Server-Sent Events 订阅 Hook
 * =========================================
 * 学习要点：
 *
 * 1. Server-Sent Events (SSE) vs WebSocket：
 *    - SSE：单向（服务器→客户端），基于 HTTP，浏览器原生支持 EventSource
 *    - WebSocket：双向，需要专门协议，适合实时聊天
 *    - 匹配进度推送是单向的，SSE 更适合
 *
 * 2. EventSource API：
 *    - new EventSource(url)：建立 SSE 连接
 *    - onmessage：每条 "data: xxx\n\n" 消息的回调
 *    - onerror：连接错误回调（浏览器默认会自动重连）
 *    - close()：手动关闭连接
 *
 * 3. 为什么 token 放 query param：
 *    - EventSource 不支持设置自定义 HTTP Header（浏览器限制）
 *    - 将 JWT token 放在 URL query string 中传递
 *    - HTTPS 下 URL 参数也是加密的，安全性可接受
 *
 * 4. useRef 保存 EventSource 实例：
 *    - 不能用 useState，因为 setState 是异步的，可能导致竞态条件
 *    - useRef 保存的是对象引用，不会触发重渲染，适合"外部资源"管理
 */

import { useState, useCallback, useRef } from 'react'
import type { SSEEvent } from '@/types'

export type SSEStatus = 'idle' | 'connecting' | 'open' | 'error' | 'closed'

interface UseSSEReturn {
  events: SSEEvent[]
  status: SSEStatus
  connect: (sessionId: string, token: string) => void
  disconnect: () => void
  clearEvents: () => void
}

export function useSSE(): UseSSEReturn {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [status, setStatus] = useState<SSEStatus>('idle')
  const esRef = useRef<EventSource | null>(null)

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    setStatus('closed')
  }, [])

  const connect = useCallback((sessionId: string, token: string) => {
    // 关闭旧连接（如果有）
    if (esRef.current) {
      esRef.current.close()
    }

    setStatus('connecting')
    setEvents([])

    // 构建 SSE URL，token 通过 query string 传递
    // 学习要点：encodeURIComponent 对 token 进行 URL 编码，
    // 防止特殊字符（如 +、=）破坏 URL 格式
    const url = `/api/match/${sessionId}/stream?token=${encodeURIComponent(token)}`
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      setStatus('open')
    }

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data)

        if (data.event === 'stream_end') {
          // 服务端发出关闭信号，主动断开
          disconnect()
          return
        }

        if (data.event === 'keepalive') {
          // 心跳包，忽略
          return
        }

        setEvents((prev) => [...prev, data])
      } catch {
        console.warn('[useSSE] Failed to parse SSE event:', event.data)
      }
    }

    es.onerror = () => {
      // EventSource 在服务端关闭连接后会触发 onerror
      // 我们手动关闭，不依赖浏览器自动重连
      setStatus('error')
      es.close()
      esRef.current = null
    }
  }, [disconnect])

  const clearEvents = useCallback(() => setEvents([]), [])

  return { events, status, connect, disconnect, clearEvents }
}
