<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16">
      <el-col v-for="c in cards" :key="c.label" :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" :style="{ color: c.color }">{{ c.value }}</div>
          <div class="stat-label">{{ c.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 趋势图 -->
      <el-col :xs="24" :md="16">
        <el-card shadow="hover">
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
        <el-card shadow="hover">
          <template #header>
            <div class="card-head"><span>全方位测试五维</span></div>
          </template>
          <div class="dims">
            <div v-for="d in dims" :key="d.name" class="dim-row">
              <div class="dim-name">{{ d.name }}</div>
              <div class="dim-desc">{{ d.desc }}</div>
              <el-tag :type="d.ready ? 'success' : 'warning'" size="small">
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
  { label: '用例总数', value: stats.value.total, color: '#3b82f6' },
  { label: '测试函数', value: funcs.value, color: '#6366f1' },
  { label: '现在能跑', value: stats.value.unit, color: '#12b76a' },
  { label: '等账号激活', value: stats.value.env, color: '#f59e0b' },
])

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
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{
      type: 'line', smooth: true, data: rates, name: '通过率',
      areaStyle: { opacity: 0.12 }, itemStyle: { color: '#3b82f6' },
      lineStyle: { color: '#3b82f6' },
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
  text-align: center;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
}
.stat-label {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sub {
  font-size: 12px;
  color: #909399;
  font-weight: 400;
}
.dims {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.dim-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dim-name {
  font-weight: 600;
  width: 42px;
}
.dim-desc {
  flex: 1;
  font-size: 13px;
  color: #606266;
}
</style>
