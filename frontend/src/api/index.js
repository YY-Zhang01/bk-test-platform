import axios from 'axios'

const http = axios.create({
  baseURL: '/',
  timeout: 180000,
})

// 统一处理错误，返回 {data} 或抛出带 message 的错误
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  },
)

export const api = {
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
  // 报告
  reports: () => http.get('/api/reports').then((d) => d.reports || []),
  // AI 生成
  genInfo: () => http.get('/api/gen'),
  genGenerate: (data) => http.post('/api/gen/generate', data),
  genValidate: (data) => http.post('/api/gen/validate', data),
  genApprove: (data) => http.post('/api/gen/approve', data),
}
