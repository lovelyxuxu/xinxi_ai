/**
 * 心犀AI - TypeScript 类型定义
 * =============================
 *
 * 【学习要点】
 * 这个文件定义了前端所有核心数据结构的 TypeScript 类型。
 *
 * interface vs type：
 * - interface — 用于定义对象的"形状"（有哪些属性和方法），可以被 extends 继承
 * - type — 更灵活，可以定义联合类型、交叉类型等
 * - 一般规则：对象结构用 interface，其他用 type
 *
 * 命名约定：
 * - 类型名用 PascalCase（大驼峰），如 UserProfile
 * - 可选属性用 ? 标记，如 nickname?: string
 * - 联合类型用 | 分隔，如 'idle' | 'connecting' | 'streaming'
 */

// ============================================================
//  用户相关类型
// ============================================================

/**
 * 用户资料 — 对应后端的 UserProfile 模型
 *
 * 这是整个应用最核心的数据类型。
 * 每个用户有 18 个字段，涵盖基本信息、地理信息、自我介绍和择偶要求。
 */
export interface UserProfile {
  user_id: string           // 用户唯一标识（如 "F001", "M002"）
  nickname: string          // 昵称
  gender: 'male' | 'female' // 性别
  age: number               // 年龄
  city: string              // 城市
  province: string          // 省份
  education: string         // 学历
  annual_income: string     // 年收入
  marital_status: string    // 婚姻状况
  mbti: string              // MBTI 性格类型

  // 择偶要求
  target_gender: 'male' | 'female'  // 期望性别
  target_age_min: number             // 期望最小年龄
  target_age_max: number             // 期望最大年龄
  target_city: string                // 期望城市（"不限"表示不限制）

  // 自由文本
  about_me: string          // 自我介绍
  ideal_partner: string     // 理想的另一半
  hobbies: string           // 兴趣爱好（逗号分隔）

  // 元数据
  created_at?: string       // 创建时间（可选，后端生成）
}

/**
 * 创建用户的请求参数
 *
 * 【学习要点】
 * Omit<UserProfile, 'user_id' | 'created_at'> 的意思是：
 * "使用 UserProfile 的所有字段，但排除 user_id 和 created_at"
 * 因为这两个字段是后端自动生成的，前端创建时不需要提供。
 *
 * 这比手动复制一遍字段要好得多——如果 UserProfile 新增字段，
 * UserCreate 会自动继承，不会出现两边不一致的问题。
 */
export type UserCreate = Omit<UserProfile, 'user_id' | 'created_at'>

/**
 * 更新用户的请求参数
 *
 * Partial<UserProfile> 的意思是：UserProfile 的所有字段都变成可选的。
 * 这样前端只需要传递想要修改的字段，后端做 partial update。
 */
export type UserUpdate = Partial<UserProfile>

// ============================================================
//  匹配相关类型
// ============================================================

/**
 * 匹配候选人 — 单次匹配中的一个推荐结果
 */
export interface MatchCandidate {
  user_id: string    // 候选人 ID
  nickname: string   // 候选人昵称
  score: number      // 匹配分数（0-100）
  reason: string     // AI 给出的推荐理由
}

/**
 * 单次匹配结果
 *
 * 一次匹配会产生多个候选人推荐和对应的推荐信。
 * agent_log 记录了 Agent 执行过程中每个节点的日志。
 */
export interface MatchResult {
  match_id: string              // 匹配记录 ID
  user_id: string               // 发起匹配的用户 ID
  candidates: MatchCandidate[]  // 推荐的候选人列表
  match_letters: string[]       // 每位候选人的缘分推荐信
  created_at: string            // 匹配时间
  agent_log: string[]           // Agent 执行日志
}

// ============================================================
//  WebSocket 相关类型
// ============================================================

/**
 * WebSocket 匹配事件 — 匹配过程中后端推送的消息
 *
 * 【学习要点】
 * 这是一个"带标签的联合类型"（Tagged Union / Discriminated Union）
 * 通过 type 字段区分不同的事件类型，TypeScript 会自动做类型收窄：
 *   if (event.type === 'node_start') { event.node } ← TS 知道这里有 node 字段
 */
export type WsMatchEvent =
  | { type: 'start'; user_id: string; nickname: string; message: string }
  | { type: 'node_start'; node: string; emoji: string; label: string; message: string }
  | { type: 'node_end'; node: string; message: string }
  | { type: 'complete'; result: MatchResult }
  | { type: 'error'; message: string }

/**
 * WebSocket 访谈事件 — AI 访谈过程中后端推送的消息
 */
export type WsInterviewEvent =
  | { type: 'ai_message'; message: string; is_complete?: boolean }
  | { type: 'system'; message: string }
  | { type: 'error'; message: string }

// ============================================================
//  UI 状态类型
// ============================================================

/**
 * 匹配 WebSocket 的连接状态
 *
 * idle — 未连接
 * connecting — 正在建立 WebSocket 连接
 * streaming — 已连接，正在接收实时事件
 * complete — 匹配完成
 */
export type MatchWsStatus = 'idle' | 'connecting' | 'streaming' | 'complete'

/**
 * AI 访谈 WebSocket 的连接状态
 */
export type ChatStatus = 'idle' | 'connecting' | 'chatting' | 'complete'

/**
 * 实时日志条目 — 匹配进度面板中显示的每一行日志
 */
export interface WsLogEntry {
  emoji: string    // 状态图标（emoji）
  text: string     // 日志文本
  active?: boolean // 是否正在执行（显示加载动画）
  done?: boolean   // 是否已完成（显示 ✓）
  error?: boolean  // 是否出错（红色显示）
}

/**
 * 聊天消息 — AI 访谈中的每条消息
 */
export interface ChatMessage {
  role: 'user' | 'ai' | 'system' | 'error'  // 消息角色
  text: string                                // 消息文本
  isComplete?: boolean                        // AI 画像是否完善标记
}

// ============================================================
//  API 响应类型
// ============================================================

/**
 * 用户公开主页（发现页/公开资料，不含私密字段）
 */
export interface UserPublic {
  user_id: string
  nickname: string
  gender: string
  age?: number | null
  city?: string | null
  province?: string | null
  education?: string | null
  annual_income?: string | null
  marital_status?: string | null
  mbti?: string | null
  height_cm?: number | null
  about_me: string
  hobbies: string
  avatar_url?: string | null
  photos: string[]
  birth_date?: string | null
  zodiac_sign?: string | null
  chinese_zodiac?: string | null
  profile_complete?: boolean
  created_at?: string
}

/**
 * 用户列表 API 响应
 */
export interface UserListResponse {
  users: UserPublic[]   // 公开用户列表
  total: number         // 总数（用于分页）
  page: number          // 当前页码
  page_size: number     // 每页数量
}

/**
 * 匹配历史 API 响应
 */
export interface MatchHistoryResponse {
  records: MatchResult[]  // 匹配记录列表
  total: number           // 总数
}

/**
 * 通用消息响应
 */
export interface MessageResponse {
  message: string
  success: boolean
  data?: Record<string, unknown>  // 可选的附加数据
}

// ============================================================
//  v2 认证相关类型
// ============================================================

/**
 * 认证用户 — 登录/注册后返回的完整用户信息
 */
export interface AuthUser {
  user_id: string
  nickname: string
  gender: string
  age?: number | null
  city?: string | null
  province?: string | null
  education?: string | null
  annual_income?: string | null
  marital_status?: string | null
  mbti?: string | null
  height_cm?: number | null
  about_me?: string | null
  ideal_partner?: string | null
  hobbies?: string | null
  target_gender?: string | null
  target_age_min?: number | null
  target_age_max?: number | null
  target_city?: string | null
  target_height_min?: number | null
  target_height_max?: number | null
  target_education?: string | null
  avatar_url?: string | null
  photos?: string[]
  birth_date?: string | null
  zodiac_sign?: string | null
  chinese_zodiac?: string | null
  profile_complete: boolean
  created_at?: string
  // Token（仅注册/登录时返回）
  access_token?: string
  refresh_token?: string
}

/**
 * 登录请求参数（支持手机号/邮箱/user_id）
 */
export interface LoginRequest {
  account: string   // 手机号、邮箱或用户ID
  password: string
}

/**
 * 简化注册请求参数（v3 只需 4 个字段）
 */
export interface RegisterRequest {
  nickname: string
  gender: '男' | '女'
  phone: string
  password: string
}

/**
 * Token 刷新响应
 */
export interface TokenRefreshResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// ============================================================
//  v3 缘分分析相关类型
// ============================================================

/** 心动清单 - 单条候选者记录 */
export interface FateCandidateItem {
  candidate_id: string
  note?: string | null
  added_at: string
  candidate: UserPublic
}

/** 心动清单列表响应 */
export interface FateCandidateListResponse {
  items: FateCandidateItem[]
  total: number
}

/** 发起缘分分析的请求体 */
export interface FateAnalysisCreate {
  analysis_type: 'group_overview' | 'deep_compatibility' | 'comm_advice' | 'comparison'
  candidate_ids: string[]
  match_params_override?: Record<string, unknown> | null
  parent_analysis_id?: string | null
}

/** 缘分分析记录 */
export interface FateAnalysisRecord {
  analysis_id: string
  analysis_type: string
  candidate_ids: string[]
  result: Record<string, unknown> | null
  status: 'pending' | 'done' | 'failed'
  created_at: string
}

/** 通知记录 */
export interface NotificationItem {
  notif_id: string
  type: string
  actor_id?: string | null
  payload: Record<string, unknown>
  is_read: boolean
  created_at: string
}

/** 通知列表响应 */
export interface NotificationListResponse {
  items: NotificationItem[]
  unread_count: number
}

/** 临时偏好参数（发起分析时可覆盖） */
export interface MatchParams {
  target_age_min?: number
  target_age_max?: number
  target_city?: string
  target_height_min?: number
  target_height_max?: number
  target_education?: string
}
