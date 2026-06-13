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
  UserPublic,
  UserCreate,
  UserUpdate,
  UserListResponse,
  MatchResult,
  MatchHistoryResponse,
  MessageResponse,
  AuthUser,
  LoginRequest,
  RegisterRequest,
  TokenRefreshResponse,
  FateCandidateListResponse,
  FateAnalysisCreate,
  FateAnalysisRecord,
  NotificationListResponse,
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
//  JWT Token 管理（v2 新增）
// ============================================================

/**
 * 【学习要点】
 * Token 存储在模块级变量中（而非 localStorage），
 * 因为 localStorage 存在 XSS 攻击风险。
 * 对于学习项目，内存存储足够安全且简单。
 *
 * 如果需要持久化（刷新页面后保持登录），
 * 可以改为 sessionStorage 或配合 httpOnly cookie。
 */
let accessToken: string | null = null
let refreshToken: string | null = null

/** 设置 Token（登录/注册成功后调用） */
export const setTokens = (access: string, refresh: string) => {
  accessToken = access
  refreshToken = refresh
}

/** 清除 Token（登出时调用） */
export const clearTokens = () => {
  accessToken = null
  refreshToken = null
}

/** 获取当前 Access Token（供 WebSocket 连接等场景使用） */
export const getAccessToken = (): string | null => accessToken

/** 获取当前 Refresh Token */
export const getRefreshToken = (): string | null => refreshToken

/** 是否有有效的 Token */
export const hasToken = (): boolean => !!accessToken

// ============================================================
//  请求拦截器 — 自动附加 Authorization 头
// ============================================================

/**
 * 【学习要点】
 * Axios 拦截器（interceptor）在请求发出前/响应返回后自动执行。
 *
 * 请求拦截器：在每个请求的 headers 中添加 Authorization: Bearer <token>
 * 这样每个 API 调用都不需要手动传 Token，DRY（Don't Repeat Yourself）。
 */
api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
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

// ============================================================
//  v2 认证接口
// ============================================================

/**
 * 用户登录
 * @param data - 登录请求（account 可以是邮箱或 user_id）
 *
 * 登录成功后返回 AuthUser（包含 access_token 和 refresh_token）
 */
export const login = (data: LoginRequest): Promise<AxiosResponse<AuthUser>> =>
  api.post('/auth/login', data)

/**
 * 用户注册
 * @param data - 注册请求（包含用户资料 + 密码）
 *
 * 注册成功后返回 AuthUser（包含 Token，无需再次登录）
 */
export const register = (data: RegisterRequest): Promise<AxiosResponse<AuthUser>> =>
  api.post('/auth/register', data)

/**
 * 刷新 Token
 * 当 access_token 过期时，用 refresh_token 换取新的 access_token
 */
export const refreshAuthToken = (token: string): Promise<AxiosResponse<TokenRefreshResponse>> =>
  api.post('/auth/refresh', { refresh_token: token })

/**
 * 获取当前登录用户的资料（需要 JWT 鉴权）
 */
export const getMe = (): Promise<AxiosResponse<AuthUser>> =>
  api.get('/auth/me')

/**
 * 编辑当前登录用户的资料（部分更新）
 */
export const updateMe = (data: Partial<AuthUser>): Promise<AxiosResponse<AuthUser>> =>
  api.put('/auth/me', data)

/**
 * 上传头像
 * 前端用 browser-image-compression 压缩后传入 File 对象
 */
export const uploadAvatar = (file: File): Promise<AxiosResponse<{ url: string; message: string }>> => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/auth/me/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 上传照片
 * @returns 包含新照片 URL 和完整照片列表
 */
export const uploadPhoto = (file: File): Promise<AxiosResponse<{ url: string; photos: string[] }>> => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/auth/me/photos', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 删除指定索引的照片
 */
export const deletePhoto = (index: number): Promise<AxiosResponse<{ url: string; photos: string[] }>> =>
  api.delete(`/auth/me/photos/${index}`)

/**
 * 获取用户公开主页
 */
export const getUserPublic = (userId: string): Promise<AxiosResponse<UserPublic>> =>
  api.get(`/users/${userId}`)

// ============================================================
//  v3 心动 TA 们 + 缘分分析接口
// ============================================================

/** 加入心动清单 */
export const addFateCandidate = (
  candidateId: string,
): Promise<AxiosResponse<{ message: string; mutual_fate: boolean }>> =>
  api.post(`/fate/candidates/${candidateId}`)

/** 从心动清单移除 */
export const removeFateCandidate = (candidateId: string): Promise<AxiosResponse<void>> =>
  api.delete(`/fate/candidates/${candidateId}`)

/** 获取我的心动清单 */
export const getFateCandidates = (): Promise<AxiosResponse<FateCandidateListResponse>> =>
  api.get('/fate/candidates')

/** 检查是否已将某用户加入心动清单 */
export const getCandidateStatus = (
  targetUserId: string,
): Promise<AxiosResponse<{ is_hearted: boolean }>> =>
  api.get(`/fate/candidates/status/${targetUserId}`)

/** 发起缘分分析（后台异步执行，立即返回 analysis_id） */
export const createFateAnalysis = (
  data: FateAnalysisCreate,
): Promise<AxiosResponse<FateAnalysisRecord>> =>
  api.post('/fate/analyses', data)

/** 获取单条分析结果（前端轮询到 status=done） */
export const getFateAnalysis = (
  analysisId: string,
): Promise<AxiosResponse<FateAnalysisRecord>> =>
  api.get(`/fate/analyses/${analysisId}`)

/** 获取历史分析列表 */
export const listFateAnalyses = (): Promise<AxiosResponse<FateAnalysisRecord[]>> =>
  api.get('/fate/analyses')

// ============================================================
//  v3 通知接口
// ============================================================

/** 获取通知列表 */
export const getNotifications = (): Promise<AxiosResponse<NotificationListResponse>> =>
  api.get('/notifications')

/** 标记单条通知已读 */
export const markNotificationRead = (notifId: string): Promise<AxiosResponse<void>> =>
  api.put(`/notifications/${notifId}/read`)

/** 全部标记已读 */
export const markAllNotificationsRead = (): Promise<AxiosResponse<void>> =>
  api.put('/notifications/read-all')

/** 获取未读通知数量（Navbar 角标用） */
export const getUnreadCount = (): Promise<AxiosResponse<{ unread_count: number }>> =>
  api.get('/notifications/unread-count')

export default api
