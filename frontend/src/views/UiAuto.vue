<template>
  <div>
    <el-card shadow="never">
      <el-alert
        :title="note"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />
      <div class="head-row">
        <div>
          <span class="count">{{ uiTests.length }}</span> 个 UI 测试
        </div>
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
    </el-card>

    <div v-for="g in groups" :key="g.name" class="group-card">
      <el-card shadow="never">
        <template #header>
          <div class="card-head">
            <div class="group-title">
              <el-icon :size="16" :color="g.color"><component :is="g.icon" /></el-icon>
              <span>{{ g.name }}</span>
              <el-tag size="small" type="info">{{ g.tests.length }}</el-tag>
            </div>
          </div>
        </template>
        <el-table :data="g.tests" size="small" stripe>
          <el-table-column prop="name" label="测试" min-width="240" />
          <el-table-column prop="desc" label="作用" min-width="320" show-overflow-tooltip />
        </el-table>
      </el-card>
    </div>

    <el-card v-if="result" shadow="never" style="margin-top: 16px">
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
import { Monitor } from '@element-plus/icons-vue'
import { api } from '@/api'

const uiTests = ref([])
const note = ref('')
const running = ref(false)
const result = ref(null)
let timer = null

// 按被测对象分组：平台 / CMDB / JOB
const groups = computed(() => {
  const meta = [
    { key: 'test_platform_ui', name: '测自己平台', icon: 'Monitor', color: '#3b82f6' },
    { key: 'test_cmdb_ui', name: '测 CMDB', icon: 'DataBoard', color: '#10b981' },
    { key: 'test_job_ui', name: '测 JOB', icon: 'Operation', color: '#8b5cf6' },
  ]
  return meta
    .map((m) => ({ ...m, tests: uiTests.value.filter((t) => t.file.startsWith(m.key)) }))
    .filter((g) => g.tests.length)
})

onMounted(async () => {
  try {
    const r = await api.uiList()
    uiTests.value = r.tests || []
    note.value = r.note || ''
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
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.count {
  font-size: 22px;
  font-weight: 700;
  color: #3b82f6;
}
.mono {
  font-family: Consolas, monospace;
  font-size: 12px;
}
.group-card {
  margin-top: 16px;
}
.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
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
}
</style>
