/**
 * 心犀AI - 路由配置
 * 定义所有页面的路由规则和整体布局。
 */
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import UserDetail from './pages/UserDetail'
import CreateUser from './pages/CreateUser'
import MatchHistory from './pages/MatchHistory'

export default function App() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 py-8 flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/user/:userId" element={<UserDetail />} />
          <Route path="/create" element={<CreateUser />} />
          <Route path="/history" element={<MatchHistory />} />
        </Routes>
      </main>
      {/* 页脚 */}
      <footer className="text-center py-6 text-sm text-gray-400">
        心犀AI · 基于 Agent + Hybrid RAG 的智能婚恋匹配系统
      </footer>
    </div>
  )
}
