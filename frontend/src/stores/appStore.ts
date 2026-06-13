/**
 * 心犀AI - 全局应用状态（Zustand）
 * ==================================
 *
 * 学习要点 — Zustand vs React Context:
 * - Context 适合低频更新的全局状态（如认证状态、主题）
 * - Zustand 适合高频更新或需要在多处独立订阅的状态
 *
 * Zustand 使用方式：
 * 1. 无需 Provider 包裹，直接 import useAppStore 即可
 * 2. 选择性订阅：const count = useAppStore(s => s.unreadCount)
 *    只有 unreadCount 变化时组件才重渲染（不像 Context 全部重渲染）
 * 3. 操作方法与状态放在同一个 store 中，调用方便
 */
import { create } from 'zustand'

interface AppState {
  /** 未读消息数（导航栏角标） */
  unreadCount: number
  setUnreadCount: (count: number) => void
  incrementUnread: () => void
  clearUnread: () => void

  /** 是否正在匹配中（MatchCenter 页面间共享） */
  isMatching: boolean
  setIsMatching: (v: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  unreadCount: 0,
  setUnreadCount: (count) => set({ unreadCount: count }),
  incrementUnread: () => set((s) => ({ unreadCount: s.unreadCount + 1 })),
  clearUnread: () => set({ unreadCount: 0 }),

  isMatching: false,
  setIsMatching: (v) => set({ isMatching: v }),
}))
