<template>
  <div>
    <el-row :gutter="16">
      <!-- 左：表单 + 历史 -->
      <el-col :xs="24" :md="10">
        <el-card shadow="never">
          <el-form label-width="90px">
            <el-form-item label="目标系统">
              <el-radio-group v-model="target">
                <el-radio-button value="job">JOB</el-radio-button>
                <el-radio-button value="cmdb">CMDB</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="接口">
              <el-select v-model="apiName" placeholder="选择只读接口" style="width: 100%">
                <el-option v-for="a in currentApis" :key="a" :value="a" :label="a" />
              </el-select>
            </el-form-item>
            <el-form-item label="参数 JSON">
              <el-input
                v-model="paramsText"
                type="textarea"
                :rows="5"
                placeholder='{"limit": 10}   —— 留空表示不传参数'
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Promotion" :loading="loading" @click="send">
                发送
              </el-button>
              <el-tag type="info" style="margin-left: 12px">只读白名单</el-tag>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card v-if="history.length" shadow="never" style="margin-top: 16px">
          <template #header>
            <div class="card-head">
              <span>历史请求</span>
              <el-button size="small" text :icon="Refresh" @click="loadHistory">刷新</el-button>
            </div>
          </template>
          <div class="history-list">
            <div
              v-for="(h, i) in history"
              :key="i"
              class="history-item"
              @click="replay(h)"
            >
              <span class="h-tag" :class="h.ok ? 'h-ok' : 'h-err'">{{ h.ok ? '成功' : '失败' }}</span>
              <span class="h-api">{{ h.target }} · {{ h.api }}</span>
              <span class="h-time">{{ h.ts }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右：结果 -->
      <el-col :xs="24" :md="14">
        <el-card v-if="result !== null" shadow="never">
          <template #header>
            <div class="card-head">
              <span>返回结果</span>
              <div>
                <el-tag :type="ok ? 'success' : 'danger'" size="small">{{ ok ? '成功' : '失败' }}</el-tag>
                <el-button size="small" text :icon="CopyDocument" @click="copyResult">复制</el-button>
              </div>
            </div>
          </template>
          <pre class="output">{{ resultText }}</pre>
        </el-card>
        <el-empty v-else description="选接口发请求，结果会显示在这里" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { CopyDocument, Promotion, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'

const METHODS = {
  job: ['get_script_list', 'get_script_version_list', 'get_script_version_detail', 'get_job_instance_status'],
  cmdb: ['search_business', 'list_biz_hosts', 'search_host', 'execute_dynamic_group', 'search_module', 'search_set', 'search_object_attribute'],
}

const target = ref('job')
const apiName = ref(METHODS.job[0])
const paramsText = ref('')
const loading = ref(false)
const result = ref(null)
const ok = ref(false)
const history = ref([])

const currentApis = computed(() => METHODS[target.value])
const resultText = computed(() => JSON.stringify(result.value, null, 2) || '')

async function send() {
  let params = {}
  if (paramsText.value.trim()) {
    try {
      params = JSON.parse(paramsText.value)
    } catch (e) {
      result.value = { error: '参数不是合法 JSON：' + e.message }
      ok.value = false
      return
    }
  }
  loading.value = true
  try {
    const r = await api.probe({ target: target.value, api: apiName.value, params })
    ok.value = r.ok
    result.value = r
    loadHistory()
  } catch (e) {
    ok.value = false
    result.value = { error: e.message }
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    const r = await api.probeHistory()
    history.value = r.items || []
  } catch (e) {
    console.error(e)
  }
}

function replay(h) {
  target.value = h.target
  apiName.value = h.api
  result.value = null
}

async function copyResult() {
  try {
    await navigator.clipboard.writeText(resultText.value)
    ElMessage.success('已复制')
  } catch (e) {
    ElMessage.warning('复制失败')
  }
}

onMounted(loadHistory)
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
  padding: 16px;
  border-radius: 8px;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  max-height: 560px;
  overflow: auto;
  white-space: pre-wrap;
  margin: 0;
}
.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 360px;
  overflow: auto;
}
.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;
}
.history-item:hover {
  background: #f1f5f9;
}
.h-tag {
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11px;
  color: #fff;
  flex-shrink: 0;
}
.h-ok { background: #10b981; }
.h-err { background: #ef4444; }
.h-api {
  flex: 1;
  font-weight: 500;
  color: #334155;
}
.h-time {
  color: #94a3b8;
  font-family: Consolas, monospace;
  font-size: 11px;
}
</style>
