/**
 * 心犀AI - 应用入口（v2 认证版）
 * ==================================
 *
 * 【学习要点 — Provider 嵌套顺序】
 * React 的 Provider 需要从外到内嵌套，顺序很重要：
 * 1. BrowserRouter — 提供路由上下文（URL 同步）
 * 2. AuthProvider — 提供认证上下文（依赖路由的 useLocation）
 * 3. App — 应用主体
 *
 * 如果顺序反了（AuthProvider 在 BrowserRouter 外面），
 * AuthProvider 内部使用 useNavigate 等 Hook 会报错。
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import App from './App'
import './index.css'

/*
 * createRoot 需要一个 HTMLElement，这里用 document.getElementById('root')
 * 注意：getElementById 可能返回 null（如果 HTML 中没有 id="root" 的元素）
 * 所以用 ! 非空断言，告诉 TS "我确定这个元素存在"
 */
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
