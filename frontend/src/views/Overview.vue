<template>
  <div class="overview">
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

    <!-- 测试分层金字塔 -->
    <el-card class="pyramid-card">
      <template #header>
        <div class="card-head">
          <span>测试分层金字塔</span>
          <span class="sub">L1 打底 → L2 分开测 → L3 连块测，再横切边界与安全</span>
        </div>
      </template>
      <div class="pyramid">
        <div
          v-for="(g, i) in pyramid"
          :key="g.name"
          class="pyr-level"
          :style="{ width: (46 + i * 18) + '%', background: g.grad }"
          :title="`查看${g.name}用例`"
          @click="gotoGroup(g.prefix)"
        >
          <span class="pyr-name">{{ g.name }}</span>
          <span class="pyr-count">{{ g.count }}</span>
          <span class="pyr-desc">{{ g.desc }}</span>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16" class="row-gap">
      <!-- 趋势图 -->
      <el-col :xs="24" :md="15">
        <el-card class="fill-card">
          <template #header>
            <div class="card-head">
              <span>通过率趋势</span>
              <span class="sub">最近 20 次执行</span>
            </div>
          </template>
          <div ref="chartRef" class="chart"></div>
          <div class="recent-runs">
            <div class="recent-title">最近执行</div>
            <div v-if="!recentRuns.length" class="recent-empty">还没有执行记录，先去「跑测试」跑一次</div>
            <div v-for="r in recentRuns" :key="r.ts" class="recent-row">
              <span class="recent-time">{{ r.ts }}</span>
              <span class="recent-plan">{{ r.plan }}</span>
              <span class="recent-dots">
                <el-tooltip content="通过"><span class="r-dot r-passed">{{ r.passed }}</span></el-tooltip>
                <el-tooltip content="失败"><span class="r-dot r-failed">{{ r.failed }}</span></el-tooltip>
                <el-tooltip content="跳过"><span class="r-dot r-skipped">{{ r.skipped }}</span></el-tooltip>
              </span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 五维 -->
      <el-col :xs="24" :md="9">
        <el-card class="fill-card">
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
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { api } from '@/api'

const router = useRouter()

function gotoGroup(prefix) {
  router.push({ path: '/cases', query: { group: prefix } })
}

const stats = ref({ total: '-', unit: '-', env: '-' })
const funcs = ref('-')
const trendItems = ref([])
const caseGroups = ref([])
const chartRef = ref(null)
let chart = null

const cards = computed(() => [
  { label: '用例总数', value: stats.value.total, icon: 'Odometer', grad: 'linear-gradient(135deg, #3b82f6, #60a5fa)' },
  { label: '测试函数', value: funcs.value, icon: 'Files', grad: 'linear-gradient(135deg, #6366f1, #a78bfa)' },
  { label: '现在能跑', value: stats.value.unit, icon: 'CircleCheck', grad: 'linear-gradient(135deg, #10b981, #34d399)' },
  { label: '待环境', value: stats.value.env, icon: 'Clock', grad: 'linear-gradient(135deg, #f59e0b, #fbbf24)' },
])

const dotColors = ['#3b82f6', '#6366f1', '#10b981', '#f59e0b', '#8b5cf6']

const dims = computed(() => [
  { name: '功能', desc: `${stats.value.total} 个分层用例`, ready: true },
  { name: '性能', desc: 'Locust 只读压测', ready: false },
  { name: '安全', desc: '鉴权 / 越权 / 注入 / 高危', ready: false },
  { name: '边界', desc: '等价类 / 边界值 / 非法值', ready: true },
  { name: '端到端', desc: '两系统联动 · 数据契约', ready: false },
])

// 金字塔：从顶部 L3 到底部专项，宽度递增；数量从用例库分组动态取
const pyramid = computed(() => {
  const count = (prefix) => {
    const g = caseGroups.value.find((x) => x.group.startsWith(prefix))
    return g ? g.cases.reduce((s, c) => s + (c.count || 1), 0) : '-'
  }
  return [
    { name: 'L3 连块测', prefix: 'L3', count: count('L3'), desc: '两系统联动 · 数据契约', grad: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' },
    { name: 'L2 分开测', prefix: 'L2', count: count('L2'), desc: 'JOB 六链路 + CMDB 独立链路', grad: 'linear-gradient(135deg, #6366f1, #3b82f6)' },
    { name: 'L1 工具层', prefix: 'L1', count: count('L1'), desc: '测自己写的工具（不碰蓝鲸）', grad: 'linear-gradient(135deg, #3b82f6, #0ea5e9)' },
    { name: '专项横切', prefix: '专项', count: count('专项'), desc: '参数边界 + 安全', grad: 'linear-gradient(135deg, #f59e0b, #f97316)' },
  ]
})

// 最近 5 次执行（趋势图下方简表）
const recentRuns = computed(() => trendItems.value.slice(-5).reverse())

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const items = trendItems.value
  const labels = items.map((i) => i.ts || '')
  const passed = items.map((i) => i.passed || 0)
  const failed = items.map((i) => i.failed || 0)
  const skipped = items.map((i) => i.skipped || 0)
  const rates = items.map((i) => Math.round((i.rate || 0) * 100))
  chart.setOption({
    grid: { left: 40, right: 48, top: 40, bottom: 40 },
    legend: { data: ['通过', '失败', '跳过', '通过率'], top: 0, textStyle: { fontSize: 12 } },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15,23,42,.9)',
      borderWidth: 0,
      textStyle: { color: '#fff' },
    },
    xAxis: {
      type: 'category', data: labels,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { rotate: 30, fontSize: 10, color: '#94a3b8' },
    },
    yAxis: [
      {
        type: 'value', name: '用例数',
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#94a3b8' },
      },
      {
        type: 'value', name: '通过率', min: 0, max: 100,
        axisLabel: { formatter: '{value}%', color: '#94a3b8' },
        splitLine: { show: false },
      },
    ],
    series: [
      { name: '通过', type: 'bar', stack: 'total', data: passed, barMaxWidth: 22, itemStyle: { color: '#10b981' } },
      { name: '失败', type: 'bar', stack: 'total', data: failed, barMaxWidth: 22, itemStyle: { color: '#ef4444' } },
      { name: '跳过', type: 'bar', stack: 'total', data: skipped, barMaxWidth: 22, itemStyle: { color: '#f59e0b' } },
      {
        name: '通过率', type: 'line', yAxisIndex: 1, data: rates,
        smooth: true, symbol: 'circle', symbolSize: 7,
        itemStyle: { color: '#3b82f6', borderColor: '#fff', borderWidth: 2 },
        lineStyle: { color: '#3b82f6', width: 3 },
      },
    ],
  })
}

onMounted(async () => {
  try {
    const [s, t, c] = await Promise.all([api.stats(), api.trend(), api.cases()])
    stats.value = { total: s.total, unit: s.unit, env: s.env }
    trendItems.value = t.items || []
    funcs.value = c.functions
    caseGroups.value = c.groups || []
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
.overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-card {
  transition: transform 0.22s ease, box-shadow 0.22s ease;
  height: 100%;
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

/* 金字塔 */
.pyramid-card {
  margin-top: 0;
}
.pyramid {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}
.pyr-level {
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #fff;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.14);
  transition: width 0.4s ease, transform 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
}
.pyr-level:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.22);
}
.pyr-name {
  font-weight: 700;
  font-size: 14px;
  min-width: 96px;
  text-align: right;
}
.pyr-count {
  font-weight: 700;
  font-size: 16px;
  min-width: 40px;
  text-align: center;
}
.pyr-desc {
  font-size: 12px;
  opacity: 0.9;
}

.row-gap {
  margin-top: 0;
}
.fill-card {
  height: 100%;
}
.chart {
  height: 260px;
}
.recent-runs {
  margin-top: 12px;
  border-top: 1px solid #f1f5f9;
  padding-top: 10px;
}
.recent-title {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 8px;
}
.recent-empty {
  font-size: 12px;
  color: #94a3b8;
  padding: 8px 0;
}
.recent-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 5px 0;
  font-size: 12px;
}
.recent-time {
  color: #94a3b8;
  font-family: Consolas, monospace;
  min-width: 90px;
}
.recent-plan {
  flex: 1;
  color: #475569;
}
.recent-dots {
  display: flex;
  gap: 8px;
}
.r-dot {
  padding: 1px 7px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
}
.r-passed { background: #10b981; }
.r-failed { background: #ef4444; }
.r-skipped { background: #f59e0b; }
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
  gap: 22px;
  padding: 8px 0;
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
  width: 44px;
}
.dim-desc {
  flex: 1;
  font-size: 13px;
  color: #64748b;
}
</style>
