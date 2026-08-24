import axios from 'axios'

const TOKEN_KEY = 'bk_auth_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

const http = axios.create({
  baseURL: '/',
  timeout: 180000,
})

// 请求拦截器：带上登录 token
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截器：统一返回 data；401 时清 token 并跳登录页
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      setToken('')
      if (!location.pathname.startsWith('/login')) {
        location.href = '/login'
      }
      return Promise.reject(new Error('未登录'))
    }
    const msg = err.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  },
)

export const api = {
  // 登录
  login: (username, password) => http.post('/api/login', { username, password }),
  // 总览
  stats: () => http.get('/api/stats'),
  trend: () => http.get('/api/trend'),
  // 用例库
  cases: () => http.get('/api/cases'),
  // 跑测试
  run: (data) => http.post('/api/run', null, { params: data }),
  runStatus: (task_id) => http.get(`/api/run/${task_id}`),
  // 接口调试
  probe: (data) => http.post('/api/probe', data),
  // UI 自动化
  uiList: () => http.get('/api/ui'),
  uiRun: () => http.post('/api/ui/run'),
  // 报告
  reports: () => http.get('/api/reports').then((d) => d.reports || []),
  // AI 生成
  genInfo: () => http.get('/api/gen'),
  genGenerate: (data) => http.post('/api/gen/generate', data),
  genHeal: (data) => http.post('/api/gen/heal', data, { timeout: 300000 }),
  genValidate: (data) => http.post('/api/gen/validate', data),
  genApprove: (data) => http.post('/api/gen/approve', data),
}
