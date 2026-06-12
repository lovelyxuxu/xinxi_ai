/**
 * 心犀AI - Vite 构建配置（TypeScript 版）
 * =========================================
 *
 * 【学习要点】
 * - Vite 是现代化的前端构建工具，比 Webpack 快得多（基于 ESModule）
 * - vite.config.ts 在 Node.js 环境中运行，用来配置开发服务器、插件、代理等
 * - 这里配置了三条代理规则，把前端的 /api 请求转发到后端 FastAPI 服务
 *
 * 【关键改动：路径别名】
 * - 添加了 resolve.alias 配置，把 @/ 映射到 src/ 目录
 * - 这样 import { Button } from "@/components/ui/button" 就不用写很长的相对路径
 * - 需要同时在 tsconfig.json 中配置 paths，TypeScript 才能识别这个别名
 */
import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],

  /*
   * 路径别名配置
   * "@/" → "./src/"
   * 例如：import { cn } from "@/lib/utils" → import { cn } from "./src/lib/utils"
   *
   * 为什么需要 path.resolve？
   * - __dirname 是当前文件（vite.config.ts）所在的目录（即 frontend/）
   * - path.resolve(__dirname, "./src") 得到 src/ 的绝对路径
   * - Vite 需要绝对路径才能正确解析别名
   */
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  /*
   * 开发服务器配置
   * - port: 5173 — 前端开发服务器端口
   * - proxy — API 代理规则（解决跨域问题）
   */
  server: {
    port: 5173,
    proxy: {
      /*
       * WebSocket 代理规则
       * 注意：WebSocket 路由必须放在普通 HTTP 路由前面！
       * 因为 Vite 会按顺序匹配，/api/match/ws 比 /api 更具体，需要优先匹配。
       *
       * ws: true — 告诉代理服务器这是一个 WebSocket 连接
       * changeOrigin: true — 修改请求头的 Host 字段，防止后端拒绝
       */
      '/api/match/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
      '/api/interview/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
      // 普通 HTTP API 请求转发到后端 FastAPI 服务
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
