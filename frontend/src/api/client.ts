/**
 * 心犀AI - API 客户端（TypeScript 版）
 * ======================================
 *
 * 【学习要点】
 * - 使用 axios 实例统一管理 baseURL 和超时配置
 * - Vite 的 proxy 会把 /api 请求转发到后端 http://127.0.0.1:8000
 *
 * 【TypeScript 改进】
 * - 每个函数都标注了参数类型和返回值类型
 * - 使用泛型 AxiosResponse<T> 让响应数据的类型明确
 * - 这样在页面组件中调用时，res.data 会有完整的类型提示
 *
 * 示例：
 *   const res = await getUsers(1, 12)
 *   res.data.users  ← TypeScript 知道这是 UserProfile[]
 *   res.data.total  ← TypeScript 知道这是 number
 */
import axios, { type AxiosResponse } from 'axios'
import type {
  UserProfile,
  UserCreate,
  UserUpdate,
  UserListResponse,
  MatchResult,
  MatchHistoryResponse,
  MessageResponse,
} from '@/types'

// ============================================================
//  Axios 实例
// ============================================================

/**
 * 创建 axios 实例
 * - baseURL: '/api' — 所有请求自动加上 /api 前缀
 * - timeout: 120000 — 超时 120 秒（匹配流程涉及多次 LLM 调用，需要较长超时）
 */
const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

// ============================================================
//  用户相关接口
// ============================================================

/**
 * 获取用户列表
 * @param page     - 页码（从 1 开始）
 * @param pageSize - 每页数量（默认 12）
 * @param filters  - 可选筛选条件（gender, city）
 *
 * 【学习要点】
 * filters 用 Record<string, string> 类型，表示"键是 string，值也是 string 的对象"
 * 这比写 { [key: string]: string } 更简洁
 */
export const getUsers = (
  page: number = 1,
  pageSize: number = 12,
  filters: Record<string, string> = {}
): Promise<AxiosResponse<UserListResponse>> =>
  api.get('/users', { params: { page, page_size: pageSize, ...filters } })

/**
 * 获取单个用户详情
 * @param userId - 用户 ID（如 "F001"）
 */
export const getUser = (userId: string): Promise<AxiosResponse<UserProfile>> =>
  api.get(`/users/${userId}`)

/**
 * 创建新用户
 * @param data - 用户资料（不含 user_id，后端自动生成）
 *
 * 返回的 data 中会包含后端生成的 user_id
 */
export const createUser = (data: UserCreate): Promise<AxiosResponse<MessageResponse & { user_id: string }>> =>
  api.post('/users', data)

/**
 * 更新用户资料（部分更新）
 * @param userId - 用户 ID
 * @param data   - 要更新的字段（Partial 类型，所有字段可选）
 */
export const updateUser = (userId: string, data: UserUpdate): Promise<AxiosResponse<MessageResponse>> =>
  api.put(`/users/${userId}`, data)

/**
 * 删除用户
 */
export const deleteUser = (userId: string): Promise<AxiosResponse<MessageResponse>> =>
  api.delete(`/users/${userId}`)

// ============================================================
//  匹配相关接口
// ============================================================

/**
 * 触发 AI 匹配（同步 HTTP 方式）
 * 注意：实际使用中更推荐 WebSocket 方式（实时进度推送）
 */
export const triggerMatch = (userId: string): Promise<AxiosResponse<MatchResult>> =>
  api.post('/match', { user_id: userId })

/**
 * 获取单次匹配结果
 */
export const getMatchResult = (matchId: string): Promise<AxiosResponse<MatchResult>> =>
  api.get(`/match/${matchId}`)

/**
 * 获取用户的匹配历史记录
 */
export const getMatchHistory = (userId: string): Promise<AxiosResponse<MatchHistoryResponse>> =>
  api.get(`/match/history/${userId}`)

// ============================================================
//  系统接口
// ============================================================

/** 健康检查 — 用于确认后端服务是否正常运行 */
export const checkHealth = (): Promise<AxiosResponse<{ status: string }>> =>
  api.get('/health')

export default api
