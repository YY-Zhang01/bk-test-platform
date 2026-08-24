<template>
  <div>
    <el-card shadow="never">
      <div class="plan-row">
        <span class="label">测试计划</span>
        <el-radio-group v-model="plan">
          <el-radio-button v-for="p in plans" :key="p.value" :value="p.value">
            {{ p.label }}
          </el-radio-button>
        </el-radio-group>
        <el-button
          type="primary"
          :icon="VideoPlay"
          :loading="running"
          :disabled="running"
          @click="run"
        >
          {{ running ? '执行中…' : '执行计划' }}
        </el-button>
      </div>
    </el-card>

    <el-card v-if="result" shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-head">
          <span>执行结果</span>
          <el-tag v-if="running" type="warning" size="small">运行中</el-tag>
          <el-tag v-else-if="result.returncode === 0" type="success" size="small">完成</el-tag>
          <el-tag v-else type="danger" size="small">有失败</el-tag>
        </div>
      </template>
      <el-alert
        v-if="result.summary"
        :title="result.summary"
        :type="result.returncode === 0 ? 'success' : 'warning'"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <pre class="output">{{ result.output || '等待输出…' }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'
import { api } from '@/api'

const plans = [
  { value: 'smoke', label: '冒烟（不等账号）' },
  { value: 'regression', label: '回归' },
  { value: 'job-only', label: '只 JOB' },
  { value: 'e2e', label: '只连块测' },
  { value: 'full', label: '全量（出报告）' },
]

const plan = ref('smoke')
const running = ref(false)
const result = ref(null)
let timer = null

async function run() {
  running.value = true
  result.value = { output: '', summary: '' }
  try {
    const p = plan.value === 'full' ? null : plan.value
    const { task_id } = await api.run({ plan: p, report: plan.value === 'full' })
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
.plan-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.label {
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
