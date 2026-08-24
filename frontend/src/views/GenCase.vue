<template>
  <div>
    <el-card shadow="never">
      <el-form label-width="90px">
        <el-form-item label="接口">
          <el-select v-model="apiName" filterable placeholder="选择接口文档" style="width: 100%">
            <el-option v-for="a in apis" :key="a" :value="a" :label="a" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型 Key">
          <el-input v-model="apiKey" placeholder="留空则用服务端配置的 key" type="password" show-password />
        </el-form-item>
        <el-form-item label="额外需求">
          <el-input v-model="requirement" type="textarea" :rows="2" placeholder="如：多生成负面用例、边界值用例" />
        </el-form-item>
        <el-form-item label="自愈上限">
          <el-input-number v-model="maxRounds" :min="1" :max="5" />
          <span class="hint">生成失败时让 AI 自动修复的最多轮数</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="MagicStick" :loading="generating" @click="generate">
            {{ generating ? '生成中…' : '生成草稿' }}
          </el-button>
          <el-button type="success" :icon="RefreshRight" :loading="healing" @click="heal">
            {{ healing ? '自愈中…' : '自愈生成（生成→跑→修）' }}
          </el-button>
          <el-tag type="info" style="margin-left: 12px">共 {{ apis.length }} 个接口 · {{ model }}</el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 自愈过程时间线 -->
    <el-card v-if="rounds.length" shadow="never" style="margin-top: 16px">
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
            <el-tag :type="r.ok ? 'success' : 'danger'" size="small">
              {{ r.ok ? '通过' : '失败' }}
            </el-tag>
            <el-collapse style="flex:1" v-if="!r.ok">
              <el-collapse-item title="查看错误信息">
                <pre class="err">{{ r.output }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- 草稿代码 -->
    <el-card v-if="code" shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-head">
          <span>草稿（接口：{{ genApiName }}）</span>
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
const apiKey = ref('')
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
    const r = await api.genGenerate({ api_name: apiName.value, api_key: apiKey.value, requirement: requirement.value })
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
      api_key: apiKey.value,
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
.card-head { display: flex; justify-content: space-between; align-items: center; }
.hint { margin-left: 10px; font-size: 12px; color: #909399; }
.round-line { display: flex; align-items: flex-start; gap: 12px; }
.err {
  background: #0b1437; color: #f8b4b4; padding: 10px; border-radius: 6px;
  font-family: Consolas, monospace; font-size: 11px; line-height: 1.5;
  max-height: 200px; overflow: auto; white-space: pre-wrap; margin: 0;
}
.output {
  background: #0b1437; color: #d4d9e6; padding: 14px; border-radius: 6px;
  font-family: Consolas, monospace; font-size: 12px; line-height: 1.6;
  max-height: 480px; overflow: auto; white-space: pre-wrap;
}
</style>
