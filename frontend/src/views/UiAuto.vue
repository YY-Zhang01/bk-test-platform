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

    <el-card shadow="never" style="margin-top: 16px">
      <el-table :data="uiTests" size="default" stripe>
        <el-table-column prop="file" label="文件" width="200">
          <template #default="{ row }"><span class="mono">{{ row.file }}</span></template>
        </el-table-column>
        <el-table-column prop="name" label="测试" min-width="220" />
        <el-table-column prop="desc" label="作用" min-width="300" show-overflow-tooltip />
      </el-table>
    </el-card>

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
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Monitor } from '@element-plus/icons-vue'
import { api } from '@/api'

const uiTests = ref([])
const note = ref('')
const running = ref(false)
const result = ref(null)
let timer = null

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
