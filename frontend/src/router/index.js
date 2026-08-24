import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/overview',
    children: [
      { path: 'overview', name: 'overview', component: () => import('@/views/Overview.vue'), meta: { title: '总览', icon: 'Odometer' } },
      { path: 'run', name: 'run', component: () => import('@/views/RunTest.vue'), meta: { title: '跑测试', icon: 'VideoPlay' } },
      { path: 'probe', name: 'probe', component: () => import('@/views/Probe.vue'), meta: { title: '接口调试', icon: 'Connection' } },
      { path: 'reports', name: 'reports', component: () => import('@/views/Reports.vue'), meta: { title: '报告', icon: 'Document' } },
      { path: 'gen', name: 'gen', component: () => import('@/views/GenCase.vue'), meta: { title: 'AI 生成', icon: 'MagicStick' } },
      { path: 'cases', name: 'cases', component: () => import('@/views/CaseLibrary.vue'), meta: { title: '用例库', icon: 'List' } },
      { path: 'ui', name: 'ui', component: () => import('@/views/UiAuto.vue'), meta: { title: 'UI 自动化', icon: 'Monitor' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 蓝鲸测试平台` : '蓝鲸测试平台'
})

export default router
