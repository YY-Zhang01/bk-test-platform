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
      <div v-if="running && result.total" class="progress-row">
        <el-progress
          :percentage="Math.min(100, Math.round((result.progress || 0) / result.total * 100))"
          :stroke-width="12"
          striped
          striped-flow
        />
        <span class="progress-text">{{ result.progress || 0 }} / {{ result.total }}</span>
      </div>

      <el-alert
        v-if="result.summary"
        :title="running ? `执行中… ${result.summary}` : result.summary"
        :type="result.returncode === 0 ? 'success' : 'warning'"
        :closable="false"
        style="margin-bottom: 12px"
      />

      <!-- 失败用例结构化 -->
      <div v-if="failureList.length" class="failures">
        <div class="failures-title">
          <el-icon color="#ef4444"><CircleCloseFilled /></el-icon>
          失败用例（{{ failureList.length }}）
        </div>
        <div v-for="(f, i) in failureList" :key="i" class="fail-item">
          <div class="fail-name">{{ f.name }}</div>
          <pre class="fail-err">{{ f.error }}</pre>
        </div>
      </div>

      <pre v-if="result.output" class="output">{{ result.output }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { CircleCloseFilled, VideoPlay } from '@element-plus/icons-vue'
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

// 从 pytest 输出解析失败用例（FAILED path::name - error 行）
const failureList = computed(() => {
  const out = result.value?.output || ''
  const fails = []
  for (const line of out.split('\n')) {
    const m = line.match(/^FAILED\s+(.+?)\s+-\s+(.+)$/)
    if (m) {
      const name = m[1].split('::').pop()
      fails.push({ name, full: m[1], error: m[2] })
    }
  }
  return fails
})

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
  margin: 0;
}
.progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.progress-row .el-progress {
  flex: 1;
}
.progress-text {
  font-family: Consolas, monospace;
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
}
.failures {
  margin-bottom: 14px;
}
.failures-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #ef4444;
  margin-bottom: 10px;
}
.fail-item {
  border: 1px solid #fee2e2;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #fef2f2;
}
.fail-name {
  font-weight: 600;
  color: #dc2626;
  margin-bottom: 6px;
}
.fail-err {
  margin: 0;
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #b91c1c;
  white-space: pre-wrap;
  line-height: 1.5;
}
</style>
