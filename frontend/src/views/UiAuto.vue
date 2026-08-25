<template>
  <div>
    <!-- 顶部汇总 + 运行按钮 -->
    <el-card class="summary-card">
      <el-alert
        :title="note"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
      />
      <div class="summary-inner">
        <div class="summary-item">
          <span class="summary-num">{{ uiTests.length }}</span>
          <span class="summary-label">UI 测试</span>
        </div>
        <el-divider direction="vertical" />
        <div class="summary-item">
          <span class="summary-num">{{ groups.length }}</span>
          <span class="summary-label">被测对象</span>
        </div>
        <div class="run-btn">
          <el-button
            type="primary"
            :icon="Monitor"
            :loading="running"
            :disabled="running"
            @click="run"
          >
            {{ running ? '运行中…' : '运行 UI 测试' }}
          </el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16" class="body-row">
      <!-- 左侧被测对象分组 -->
      <el-col :xs="24" :sm="6" :md="5">
        <el-card class="group-panel">
          <div class="group-list">
            <div
              v-for="g in groups"
              :key="g.key"
              class="group-item"
              :class="{ active: g.key === activeGroup }"
              @click="activeGroup = g.key"
            >
              <div class="group-icon" :style="{ background: g.grad }">
                <el-icon :size="16" color="#fff"><component :is="g.icon" /></el-icon>
              </div>
              <div class="group-text">
                <div class="group-name">{{ g.short }}</div>
                <div class="group-sub">{{ g.sub }}</div>
              </div>
              <div class="group-count">{{ g.tests.length }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧测试列表 -->
      <el-col :xs="24" :sm="18" :md="19">
        <el-card>
          <div class="toolbar">
            <div class="toolbar-title">{{ activeGroupLabel }}</div>
            <el-input
              v-model="keyword"
              placeholder="搜索测试名 / 作用"
              clearable
              style="width: 240px"
              :prefix-icon="Search"
            />
          </div>
          <el-table :data="filteredTests" size="default" stripe>
            <el-table-column label="测试" min-width="230">
              <template #default="{ row }">
                <span class="mono">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="desc" label="作用 / 设计原因" min-width="360" show-overflow-tooltip />
          </el-table>
          <div v-if="!filteredTests.length" class="empty-tip">该分组暂无测试</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行结果 -->
    <el-card v-if="result" shadow="never" class="result-card">
      <template #header>
        <div class="card-head">
          <span>运行结果</span>
          <el-tag v-if="running" type="warning" size="small">运行中</el-tag>
          <el-tag v-else-if="result.returncode === 0" type="success" size="small">通过</el-tag>
          <el-tag v-else type="danger" size="small">有失败</el-tag>
        </div>
      </template>
      <el-alert
        v-if="result.summary"
        :title="result.summary"
        :type="result.returncode === 0 ? 'success' : 'error'"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <pre class="output">{{ result.output || '等待输出…' }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Monitor, Search } from '@element-plus/icons-vue'
import { api } from '@/api'

const uiTests = ref([])
const note = ref('')
const running = ref(false)
const result = ref(null)
const activeGroup = ref('')
const keyword = ref('')
let timer = null

const groups = computed(() => {
  const meta = [
    { key: 'test_platform_ui', short: '测自己平台', sub: '部署在服务器的平台', icon: 'Monitor', grad: 'linear-gradient(135deg, #3b82f6, #60a5fa)' },
    { key: 'test_cmdb_ui', short: '测 CMDB', sub: '蓝鲸配置平台', icon: 'DataBoard', grad: 'linear-gradient(135deg, #10b981, #34d399)' },
    { key: 'test_job_ui', short: '测 JOB', sub: '蓝鲸作业平台', icon: 'Operation', grad: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' },
  ]
  return meta
    .map((m) => ({ ...m, tests: uiTests.value.filter((t) => t.file.startsWith(m.key)) }))
    .filter((g) => g.tests.length)
})

const activeGroupLabel = computed(() => {
  const g = groups.value.find((x) => x.key === activeGroup.value)
  return g ? g.short : ''
})

const filteredTests = computed(() => {
  const g = groups.value.find((x) => x.key === activeGroup.value)
  if (!g) return []
  const kw = keyword.value.trim().toLowerCase()
  return g.tests.filter((t) => !kw || t.name.toLowerCase().includes(kw) || (t.desc || '').toLowerCase().includes(kw))
})

onMounted(async () => {
  try {
    const r = await api.uiList()
    uiTests.value = r.tests || []
    note.value = r.note || ''
    if (groups.value.length) activeGroup.value = groups.value[0].key
  } catch (e) {
    console.error(e)
  }
})

async function run() {
  running.value = true
  result.value = { output: '', summary: '' }
  try {
    const { task_id } = await api.uiRun()
    timer = setInterval(async () => {
      const r = await api.runStatus(task_id)
      result.value = r
      if (r.done) {
        clearInterval(timer)
        timer = null
        running.value = false
      }
    }, 1500)
  } catch (e) {
    running.value = false
    result.value = { output: String(e.message || e) }
  }
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
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
.run-btn {
  margin-left: auto;
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
.empty-tip {
  text-align: center;
  color: #94a3b8;
  padding: 30px 0;
}
.mono {
  font-family: Consolas, monospace;
  font-size: 12px;
}
.result-card {
  margin-top: 16px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.output {
  background: #0b1437;
  color: #d4d9e6;
  padding: 14px;
  border-radius: 6px;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  max-height: 420px;
  overflow: auto;
  white-space: pre-wrap;
  margin: 0;
}
</style>
