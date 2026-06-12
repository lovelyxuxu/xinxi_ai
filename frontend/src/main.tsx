/**
 * 心犀AI - 应用入口
 * ==================
 *
 * 【学习要点】
 * - StrictMode：React 的开发模式辅助工具，会重复渲染组件来检测副作用问题
 * - BrowserRouter：react-router-dom 的路由容器，提供 URL 同步能力
 * - 注意 import 路径从 '.jsx' 变成了不带扩展名（TypeScript 会自动解析 .tsx）
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
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
      <App />
    </BrowserRouter>
  </StrictMode>,
)
