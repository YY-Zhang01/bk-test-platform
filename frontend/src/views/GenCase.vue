<template>
  <div class="gen">
    <!-- 顶部配置区 -->
    <el-card class="config-card">
      <div class="config-head">
        <div class="config-title">
          <el-icon :size="18" color="#6366f1"><MagicStick /></el-icon>
          <span>AI 用例生成工作台</span>
        </div>
        <el-tag type="success" effect="light" size="small">模型 {{ model }} 已就绪</el-tag>
      </div>

      <div class="config-row">
        <div class="field">
          <div class="field-label">目标接口</div>
          <el-select v-model="apiName" filterable placeholder="选择接口文档" class="field-select">
            <el-option v-for="a in apis" :key="a" :value="a" :label="a" />
          </el-select>
        </div>
        <div class="field field-grow">
          <div class="field-label">额外需求（可选）</div>
          <el-input
            v-model="requirement"
            type="textarea"
            :rows="3"
            placeholder="描述你想要的用例侧重点，例如：多生成负面用例、边界值用例、参数越界场景…"
          />
        </div>
      </div>

      <div class="action-row">
        <el-button size="large" :icon="MagicStick" :loading="generating" @click="generate">
          生成草稿
        </el-button>
        <el-button size="large" type="primary" :icon="RefreshRight" :loading="healing" @click="heal">
          自愈生成（生成 → 跑 → 修）
        </el-button>
        <div class="rounds-set">
          <span class="rounds-label">自愈上限</span>
          <el-input-number v-model="maxRounds" :min="1" :max="5" size="small" />
        </div>
      </div>
    </el-card>

    <!-- 自愈过程 -->
    <el-card v-if="rounds.length" class="result-card">
      <template #header>
        <div class="card-head">
          <span>自愈过程</span>
          <el-tag v-if="healResult" :type="finalTagType" size="small">{{ finalText }}</el-tag>
        </div>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="(r, idx) in rounds"
          :key="idx"
          :type="r.ok ? 'success' : 'danger'"
          :timestamp="`第 ${r.round} 轮 · ${r.stage === 'collect' ? '收集验证' : '真跑验证'}`"
        >
          <div class="round-line">
            <el-tag :type="r.ok ? 'success' : 'danger'" size="small">{{ r.ok ? '通过' : '失败' }}</el-tag>
            <el-collapse v-if="!r.ok" style="flex:1">
              <el-collapse-item title="查看错误">
                <pre class="err">{{ r.output }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- 代码结果 -->
    <el-card v-if="code" class="result-card">
      <template #header>
        <div class="card-head">
          <span>生成草稿 · {{ genApiName }}</span>
          <div>
            <el-button size="small" :loading="validating" @click="validate">验证可收集</el-button>
            <el-button size="small" type="success" :loading="approving" @click="approve">并入 tests/</el-button>
          </div>
        </div>
      </template>
      <el-alert
        v-if="validateResult"
        :title="validateResult"
        :type="collected ? 'success' : 'error'"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <pre class="output">{{ code }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { MagicStick, RefreshRight } from '@element-plus/icons-vue'
import { api } from '@/api'

const apis = ref([])
const model = ref('deepseek-chat')
const apiName = ref('')
const requirement = ref('')
const maxRounds = ref(3)
const code = ref('')
const genApiName = ref('')
const generating = ref(false)
const healing = ref(false)
const validating = ref(false)
const approving = ref(false)
const validateResult = ref('')
const collected = ref(false)
const rounds = ref([])
const healResult = ref('')

const finalText = computed(() => ({
  passed: '✓ 自愈通过（真跑绿）',
  collect_passed: '✓ 能收集（环境用例待账号）',
  failed: '✗ 达上限，转人工',
}[healResult.value] || ''))
const finalTagType = computed(() => ({
  passed: 'success',
  collect_passed: 'success',
  failed: 'danger',
}[healResult.value] || 'info'))

onMounted(async () => {
  try {
    const info = await api.genInfo()
    apis.value = info.apis || []
    model.value = info.model
  } catch (e) {
    console.error(e)
  }
})

async function generate() {
  if (!apiName.value) { validateResult.value = '请先选择接口'; collected.value = false; return }
  generating.value = true
  validateResult.value = ''
  rounds.value = []
  healResult.value = ''
  try {
    const r = await api.genGenerate({ api_name: apiName.value, requirement: requirement.value })
    if (r.ok) { code.value = r.code; genApiName.value = r.api_name }
    else { validateResult.value = r.error; collected.value = false }
  } catch (e) {
    validateResult.value = e.message; collected.value = false
  } finally {
    generating.value = false
  }
}

async function heal() {
  if (!apiName.value) { validateResult.value = '请先选择接口'; collected.value = false; return }
  healing.value = true
  validateResult.value = ''
  rounds.value = []
  healResult.value = ''
  try {
    const r = await api.genHeal({
      api_name: apiName.value,
      requirement: requirement.value,
      max_rounds: maxRounds.value,
    })
    if (r.ok) {
      code.value = r.code
      genApiName.value = r.api_name
      rounds.value = r.rounds || []
      healResult.value = r.final
    } else {
      validateResult.value = r.error
      collected.value = false
    }
  } catch (e) {
    validateResult.value = e.message; collected.value = false
  } finally {
    healing.value = false
  }
}

async function validate() {
  validating.value = true
  try {
    const r = await api.genValidate({ api_name: genApiName.value, code: code.value })
    collected.value = r.collected
    validateResult.value = r.collected ? '✓ 可被 pytest 收集' : '收集失败：\n' + r.output
  } catch (e) {
    collected.value = false; validateResult.value = e.message
  } finally {
    validating.value = false
  }
}

async function approve() {
  approving.value = true
  try {
    const r = await api.genApprove({ api_name: genApiName.value, code: code.value })
    validateResult.value = r.ok ? `✓ 已保存到 ${r.saved}` : r.error
    collected.value = r.ok
  } catch (e) {
    validateResult.value = e.message
  } finally {
    approving.value = false
  }
}
</script>

<style scoped>
.gen {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.config-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.config-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 16px;
}
.config-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 260px;
}
.field-grow {
  flex: 1;
  min-width: 320px;
}
.field-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}
.field-select {
  width: 100%;
}
.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.rounds-set {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.rounds-label {
  font-size: 13px;
  color: #64748b;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.round-line {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.err {
  background: #0b1437; color: #f8b4b4; padding: 10px; border-radius: 6px;
  font-family: Consolas, monospace; font-size: 11px; line-height: 1.5;
  max-height: 200px; overflow: auto; white-space: pre-wrap; margin: 0;
}
.output {
  background: #0b1437; color: #d4d9e6; padding: 16px; border-radius: 8px;
  font-family: Consolas, monospace; font-size: 12px; line-height: 1.6;
  max-height: 480px; overflow: auto; white-space: pre-wrap; margin: 0;
}
</style>
