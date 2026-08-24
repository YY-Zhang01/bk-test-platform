<template>
  <div>
    <el-card shadow="never">
      <el-form label-width="90px" style="max-width: 820px">
        <el-form-item label="接口">
          <el-select
            v-model="apiName"
            filterable
            placeholder="选择接口文档"
            style="width: 100%"
          >
            <el-option v-for="a in apis" :key="a" :value="a" :label="a" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型 Key">
          <el-input v-model="apiKey" placeholder="留空则用服务端配置的 key" type="password" show-password />
        </el-form-item>
        <el-form-item label="额外需求">
          <el-input v-model="requirement" type="textarea" :rows="2" placeholder="如：多生成负面用例、边界值用例" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="MagicStick" :loading="generating" @click="generate">
            {{ generating ? '生成中…' : '生成用例草稿' }}
          </el-button>
          <el-tag type="info" style="margin-left: 12px">
            共 {{ apis.length }} 个接口文档 · 模型 {{ model }}
          </el-tag>
        </el-form-item>
      </el-form>
    </el-card>

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
import { onMounted, ref } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { api } from '@/api'

const apis = ref([])
const model = ref('deepseek-chat')
const apiName = ref('')
const apiKey = ref('')
const requirement = ref('')
const code = ref('')
const genApiName = ref('')
const generating = ref(false)
const validating = ref(false)
const approving = ref(false)
const validateResult = ref('')
const collected = ref(false)

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
  if (!apiName.value) {
    validateResult.value = '请先选择接口'
    collected.value = false
    return
  }
  generating.value = true
  validateResult.value = ''
  try {
    const r = await api.genGenerate({
      api_name: apiName.value,
      api_key: apiKey.value,
      requirement: requirement.value,
    })
    if (r.ok) {
      code.value = r.code
      genApiName.value = r.api_name
    } else {
      validateResult.value = r.error
      collected.value = false
    }
  } catch (e) {
    validateResult.value = e.message
    collected.value = false
  } finally {
    generating.value = false
  }
}

async function validate() {
  validating.value = true
  try {
    const r = await api.genValidate({ api_name: genApiName.value, code: code.value })
    collected.value = r.collected
    validateResult.value = r.collected ? '✓ 可被 pytest 收集' : '收集失败：\n' + r.output
  } catch (e) {
    collected.value = false
    validateResult.value = e.message
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
  max-height: 480px;
  overflow: auto;
  white-space: pre-wrap;
}
</style>
