import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import './style.css'
import App from './App.vue'
import Home from './views/Home.vue'
import Kid from './views/Kid.vue'
import Stranger from './views/Stranger.vue'
import Parent from './views/Parent.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Home },
    { path: '/kid', component: Kid },
    { path: '/stranger', component: Stranger },
    { path: '/join', redirect: '/stranger' },
    { path: '/parent', component: Parent },
  ],
})

createApp(App).use(router).mount('#app')
