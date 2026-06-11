/**
 * 心犀AI - API 客户端
 * 封装所有与后端的 HTTP 通信，页面组件只需调用这里的方法。
 *
 * 学习要点：
 * - 使用 axios 实例统一管理 baseURL 和错误处理
 * - Vite 的 proxy 会把 /api 请求转发到后端 http://127.0.0.1:8000
 */
import axios from 'axios'

// 创建 axios 实例，所有请求都走 /api 前缀
const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // 匹配流程可能需要较长时间（LLM 调用）
})

// ========== 用户相关接口 ==========

/** 获取用户列表 */
export const getUsers = (page = 1, pageSize = 12, filters = {}) =>
  api.get('/users', { params: { page, page_size: pageSize, ...filters } })

/** 获取单个用户详情 */
export const getUser = (userId) =>
  api.get(`/users/${userId}`)

/** 创建用户 */
export const createUser = (data) =>
  api.post('/users', data)

/** 更新用户 */
export const updateUser = (userId, data) =>
  api.put(`/users/${userId}`, data)

/** 删除用户 */
export const deleteUser = (userId) =>
  api.delete(`/users/${userId}`)

// ========== 匹配相关接口 ==========

/** 触发匹配 */
export const triggerMatch = (userId) =>
  api.post('/match', { user_id: userId })

/** 获取单次匹配结果 */
export const getMatchResult = (matchId) =>
  api.get(`/match/${matchId}`)

/** 获取匹配历史 */
export const getMatchHistory = (userId) =>
  api.get(`/match/history/${userId}`)

/** 健康检查 */
export const checkHealth = () =>
  api.get('/health')

export default api
