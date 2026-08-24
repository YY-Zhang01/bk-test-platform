<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16">
      <el-col v-for="c in cards" :key="c.label" :xs="12" :sm="6">
        <el-card class="stat-card">
          <div class="stat-inner">
            <div class="stat-icon" :style="{ background: c.grad }">
              <el-icon :size="22" color="#fff"><component :is="c.icon" /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-value">{{ c.value }}</div>
              <div class="stat-label">{{ c.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 趋势图 -->
      <el-col :xs="24" :md="16">
        <el-card>
          <template #header>
            <div class="card-head">
              <span>通过率趋势</span>
              <span class="sub">最近 20 次执行</span>
            </div>
          </template>
          <div ref="chartRef" style="height: 340px"></div>
        </el-card>
      </el-col>

      <!-- 五维 -->
      <el-col :xs="24" :md="8">
        <el-card>
          <template #header>
            <div class="card-head"><span>全方位测试五维</span></div>
          </template>
          <div class="dims">
            <div v-for="(d, i) in dims" :key="d.name" class="dim-row">
              <div class="dim-dot" :style="{ background: dotColors[i] }"></div>
              <div class="dim-name">{{ d.name }}</div>
              <div class="dim-desc">{{ d.desc }}</div>
              <el-tag :type="d.ready ? 'success' : 'warning'" size="small" effect="light">
                {{ d.ready ? '已落地' : '待账号' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { api } from '@/api'

const stats = ref({ total: '-', unit: '-', env: '-' })
const funcs = ref('-')
const trendItems = ref([])
const chartRef = ref(null)
let chart = null

const cards = computed(() => [
  { label: '用例总数', value: stats.value.total, icon: 'Odometer', grad: 'linear-gradient(135deg, #3b82f6, #60a5fa)' },
  { label: '测试函数', value: funcs.value, icon: 'Files', grad: 'linear-gradient(135deg, #6366f1, #a78bfa)' },
  { label: '现在能跑', value: stats.value.unit, icon: 'CircleCheck', grad: 'linear-gradient(135deg, #10b981, #34d399)' },
  { label: '等账号激活', value: stats.value.env, icon: 'Clock', grad: 'linear-gradient(135deg, #f59e0b, #fbbf24)' },
])

const dotColors = ['#3b82f6', '#6366f1', '#10b981', '#f59e0b', '#8b5cf6']

const dims = computed(() => [
  { name: '功能', desc: `${stats.value.total} 个分层用例`, ready: true },
  { name: '性能', desc: 'Locust 只读压测', ready: false },
  { name: '安全', desc: '鉴权 / 越权 / 注入 / 高危', ready: false },
  { name: '边界', desc: '等价类 / 边界值 / 非法值', ready: true },
  { name: '端到端', desc: '两系统联动 · 数据契约', ready: false },
])

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const items = trendItems.value
  const labels = items.map((i) => i.ts || '')
  const rates = items.map((i) => Math.round((i.rate || 0) * 100))
  chart.setOption({
    grid: { left: 40, right: 16, top: 20, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15,23,42,.9)',
      borderWidth: 0,
      textStyle: { color: '#fff' },
    },
    xAxis: {
      type: 'category', data: labels, boundaryGap: false,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { rotate: 30, fontSize: 10, color: '#94a3b8' },
    },
    yAxis: {
      type: 'value', min: 0, max: 100,
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { formatter: '{value}%', color: '#94a3b8' },
    },
    series: [{
      type: 'line', smooth: true, data: rates, name: '通过率',
      symbol: 'circle', symbolSize: 7,
      itemStyle: { color: '#3b82f6', borderColor: '#fff', borderWidth: 2 },
      lineStyle: { color: '#3b82f6', width: 3 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,130,246,.30)' },
          { offset: 1, color: 'rgba(59,130,246,.02)' },
        ]),
      },
    }],
  })
}

onMounted(async () => {
  try {
    const [s, t, c] = await Promise.all([api.stats(), api.trend(), api.cases()])
    stats.value = { total: s.total, unit: s.unit, env: s.env }
    trendItems.value = t.items || []
    funcs.value = c.functions
    await nextTick()
    renderChart()
  } catch (e) {
    console.error(e)
  }
})

onBeforeUnmount(() => {
  if (chart) chart.dispose()
})
</script>

<style scoped>
.stat-card {
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12) !important;
}
.stat-inner {
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.16);
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.1;
  color: #1e293b;
}
.stat-label {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 13px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sub {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 400;
}
.dims {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.dim-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dim-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dim-name {
  font-weight: 600;
  width: 40px;
}
.dim-desc {
  flex: 1;
  font-size: 13px;
  color: #64748b;
}
</style>
