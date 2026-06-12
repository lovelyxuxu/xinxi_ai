import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // WebSocket 匹配路由（必须放在 /api 前面，优先匹配）
      '/api/match/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,           // 启用 WebSocket 代理
        changeOrigin: true,
      },
      // WebSocket 访谈路由（必须放在 /api 前面，优先匹配）
      '/api/interview/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
      // HTTP API 请求转发到后端 FastAPI 服务
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
