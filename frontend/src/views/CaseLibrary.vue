<template>
  <div>
    <!-- 顶部统计 -->
    <el-card class="summary-card">
      <div class="summary-inner">
        <div class="summary-item">
          <span class="summary-num">{{ total }}</span>
          <span class="summary-label">用例总数</span>
        </div>
        <el-divider direction="vertical" />
        <div class="summary-item">
          <span class="summary-num">{{ functions }}</span>
          <span class="summary-label">测试函数</span>
        </div>
        <el-divider direction="vertical" />
        <div class="summary-item">
          <span class="summary-num">{{ runnable }}</span>
          <span class="summary-label">现在能跑</span>
        </div>
        <el-divider direction="vertical" />
        <div class="summary-item">
          <span class="summary-num">{{ waiting }}</span>
          <span class="summary-label">等账号激活</span>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16" class="body-row">
      <!-- 左侧分组导航 -->
      <el-col :xs="24" :sm="6" :md="5">
        <el-card class="group-panel">
          <div class="group-list">
            <div
              v-for="g in groups"
              :key="g.group"
              class="group-item"
              :class="{ active: g.group === activeGroup }"
              @click="activeGroup = g.group"
            >
              <div class="group-icon" :style="{ background: g.grad }">
                <el-icon :size="16" color="#fff"><component :is="g.icon" /></el-icon>
              </div>
              <div class="group-text">
                <div class="group-name">{{ g.short }}</div>
                <div class="group-sub">{{ g.sub }}</div>
              </div>
              <div class="group-count">{{ g.count }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧当前分组表格 -->
      <el-col :xs="24" :sm="18" :md="19">
        <el-card>
          <div class="toolbar">
            <div class="toolbar-title">{{ activeGroupLabel }}</div>
            <div class="toolbar-filters">
              <el-input
                v-model="keyword"
                placeholder="搜索用例名 / 作用"
                clearable
                style="width: 240px"
                :prefix-icon="Search"
              />
              <el-radio-group v-model="envFilter" size="default">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="否">可跑</el-radio-button>
                <el-radio-button label="是">等账号</el-radio-button>
              </el-radio-group>
            </div>
          </div>

          <el-table :data="currentCases" size="default" stripe>
            <el-table-column label="用例" min-width="240">
              <template #default="{ row }">
                <div class="case-name">{{ row.name }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="desc" label="作用 / 设计原因" min-width="320" show-overflow-tooltip />
            <el-table-column prop="marker" label="marker" width="140">
              <template #default="{ row }">
                <span class="mono">{{ row.marker || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.env === '否' ? 'success' : 'warning'" size="small">
                  {{ row.env === '否' ? '可跑' : '等账号' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!currentCases.length" class="empty-tip">没有匹配的用例</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { api } from '@/api'

const total = ref('-')
const functions = ref('-')
const groups = ref([])
const activeGroup = ref('')
const keyword = ref('')
const envFilter = ref('all')

const GROUP_META = {
  L1: { short: '工具层', sub: '测自己写的工具', icon: 'Tools', grad: 'linear-gradient(135deg, #0ea5e9, #3b82f6)' },
  L2: { short: '分开测', sub: '两系统各自单独测', icon: 'Connection', grad: 'linear-gradient(135deg, #6366f1, #3b82f6)' },
  L3: { short: '连块测', sub: '两系统联动', icon: 'Link', grad: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' },
  专项: { short: '专项横切', sub: '边界 + 安全', icon: 'Aim', grad: 'linear-gradient(135deg, #f59e0b, #f97316)' },
}

const runnable = ref('-')
const waiting = ref('-')

const activeGroupLabel = computed(() => {
  const g = groups.value.find((x) => x.group === activeGroup.value)
  return g ? g.group : ''
})

const currentCases = computed(() => {
  const g = groups.value.find((x) => x.group === activeGroup.value)
  if (!g) return []
  const kw = keyword.value.trim().toLowerCase()
  return g.cases.filter((c) => {
    const matchKw = !kw || c.name.toLowerCase().includes(kw) || (c.desc || '').toLowerCase().includes(kw)
    const matchEnv = envFilter.value === 'all' || c.env === envFilter.value
    return matchKw && matchEnv
  })
})

onMounted(async () => {
  try {
    const data = await api.cases()
    total.value = data.total
    functions.value = data.functions
    const raw = data.groups || []
    groups.value = raw.map((g) => {
      const prefix = Object.keys(GROUP_META).find((k) => g.group.startsWith(k)) || ''
      const meta = GROUP_META[prefix] || { short: g.group, sub: '', icon: 'List', grad: 'linear-gradient(135deg,#64748b,#94a3b8)' }
      const count = g.cases.reduce((s, c) => s + (c.count || 1), 0)
      return { ...g, ...meta, count }
    })
    if (groups.value.length) activeGroup.value = groups.value[0].group
    let run = 0
    let wait = 0
    raw.forEach((g) => g.cases.forEach((c) => {
      if (c.env === '否') run += (c.count || 1)
      else wait += (c.count || 1)
    }))
    runnable.value = run
    waiting.value = wait
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.summary-card {
  margin-bottom: 16px;
}
.summary-inner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
}
.summary-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.summary-num {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.summary-label {
  color: #94a3b8;
  font-size: 13px;
}

.body-row {
  margin-top: 0;
}
.group-panel {
  height: 100%;
}
.group-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.group-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}
.group-item:hover {
  background: #f1f5f9;
}
.group-item.active {
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.1));
  border-color: rgba(59, 130, 246, 0.3);
}
.group-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.group-text {
  flex: 1;
  min-width: 0;
}
.group-name {
  font-weight: 600;
  font-size: 14px;
}
.group-sub {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.group-count {
  font-size: 16px;
  font-weight: 700;
  color: #3b82f6;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.toolbar-title {
  font-weight: 600;
  font-size: 16px;
}
.toolbar-filters {
  display: flex;
  gap: 12px;
  align-items: center;
}
.case-name {
  font-weight: 500;
}
.mono {
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #909399;
}
.empty-tip {
  text-align: center;
  color: #94a3b8;
  padding: 30px 0;
}
</style>
