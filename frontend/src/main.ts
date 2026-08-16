import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'
import App from './App.vue'
import router from './router'
import './styles.css'

// 全局注册 Naive UI 组件，避免页面里使用 n-button / n-input 等组件时运行期无法解析。
createApp(App).use(createPinia()).use(router).use(naive).mount('#app')
