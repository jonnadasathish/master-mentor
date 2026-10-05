import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { installGlobalErrorHandling } from './errors'
import { createAppRouter } from './router'

const app = createApp(App)
app.use(createPinia())
app.use(createAppRouter())
installGlobalErrorHandling(app)
app.mount('#app')
