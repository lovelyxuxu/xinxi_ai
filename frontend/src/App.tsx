/**
 * 心犀AI - 路由配置（TypeScript 版）
 * ====================================
 *
 * 【学习要点】
 * - Routes + Route：react-router-dom v6 的路由声明方式
 * - path="/user/:userId" 中的 :userId 是动态路由参数
 *   在组件内通过 useParams() 获取，如 { userId: "F001" }
 * - 整体布局：Navbar（顶部导航）+ main（内容区）+ footer（页脚）
 */
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import UserDetail from './pages/UserDetail'
import CreateUser from './pages/CreateUser'
import MatchHistory from './pages/MatchHistory'
import Profile from './pages/Profile'

export default function App() {
  return (
    <div className="min-h-screen">
      {/* 顶部导航栏 — 固定在页面顶部，所有页面共享 */}
      <Navbar />

      {/* 主内容区 — 根据 URL 渲染不同的页面组件 */}
      <main className="max-w-6xl mx-auto px-6 py-8 flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/user/:userId" element={<UserDetail />} />
          <Route path="/create" element={<CreateUser />} />
          <Route path="/history" element={<MatchHistory />} />
          <Route path="/profile/:userId" element={<Profile />} />
        </Routes>
      </main>

      {/* 页脚 */}
      <footer className="text-center py-6 text-sm text-gray-400">
        心犀AI · 基于 Agent + Hybrid RAG 的智能婚恋匹配系统
      </footer>
    </div>
  )
}
