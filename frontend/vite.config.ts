import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  server: {
    port: 5173,
    proxy: {
      // 前端请求 /backend-api/*，开发期转发到 FastAPI 的 /api/*。
      '/backend-api': {
        // 8000 可能被其他本地服务占用；本项目后端默认运行在 8001。
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/backend-api/, '/api')
      }
    }
  }
})
