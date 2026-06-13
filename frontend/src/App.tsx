/**
 * 心犀AI - 路由配置（v3 完整版）
 * ===================================
 *
 * 【v3 变更】
 * - 新增移动端底部导航栏 BottomNav（md 以下显示）
 * - 新增 /profile 个人中心、/profile/edit 编辑资料路由
 * - main 区域在移动端增加底部 padding（pb-20），避免被底部导航遮挡
 * - 桌面端保留 footer，移动端不显示（被底部导航替代）
 *
 * 【路由说明】
 * - 公开页面（无需登录）：首页、用户详情、登录、注册
 * - 受保护页面（需要登录）：匹配历史、个人中心、编辑资料、匹配中心
 */
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import BottomNav from './components/BottomNav'
import ProtectedRoute from './components/ProtectedRoute'
import Home from './pages/Home'
import UserDetail from './pages/UserDetail'
import Login from './pages/Login'
import Register from './pages/Register'
import MatchHistory from './pages/MatchHistory'
import MyProfile from './pages/MyProfile'
import EditProfile from './pages/EditProfile'
import FateList from './pages/FateList'
import FateAnalysis from './pages/FateAnalysis'
import MatchCenter from './pages/MatchCenter'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* 顶部导航栏（桌面端） */}
      <Navbar />

      {/* 主内容区
          pb-20 md:pb-8: 移动端底部给 BottomNav 留出空间，桌面端正常 */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full pb-20 md:pb-8">
        <Routes>
          {/* === 公开页面 === */}
          <Route path="/" element={<Home />} />
          <Route path="/user/:userId" element={<UserDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* === 受保护页面（需要登录） === */}
          <Route path="/history" element={
            <ProtectedRoute><MatchHistory /></ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute><MyProfile /></ProtectedRoute>
          } />
          <Route path="/profile/edit" element={
            <ProtectedRoute><EditProfile /></ProtectedRoute>
          } />

          {/* === v3: 心动清单 + 缘分分析 === */}
          <Route path="/fate" element={
            <ProtectedRoute><FateList /></ProtectedRoute>
          } />
          <Route path="/fate/analysis/:analysisId" element={
            <ProtectedRoute requireProfileComplete><FateAnalysis /></ProtectedRoute>
          } />

          {/* Phase 3c: 匹配中心（SSE + HITL） */}
          <Route path="/match" element={
            <ProtectedRoute><MatchCenter /></ProtectedRoute>
          } />

          {/* Phase 4 将添加：/chat、/chat/:convId、/social */}
          {/* Phase 5 将添加：/settings */}
        </Routes>
      </main>

      {/* 移动端底部导航（md 以下显示） */}
      <BottomNav />

      {/* 桌面端页脚（移动端隐藏） */}
      <footer
        className="hidden md:block text-center py-4 text-xs"
        style={{ color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border)' }}
      >
        心犀AI · 基于 Agent + LangGraph + RAG 的智能婚恋匹配系统
      </footer>
    </div>
  )
}
