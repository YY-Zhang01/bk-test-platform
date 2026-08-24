<template>
  <div>
    <el-card shadow="never">
      <el-form label-width="90px" style="max-width: 720px">
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
            :rows="4"
            placeholder='{"limit": 10}   —— 留空表示不传参数'
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Promotion" :loading="loading" @click="send">
            发送
          </el-button>
          <el-tag type="info" style="margin-left: 12px">只读白名单，写操作一律拒绝</el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="result !== null" shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-head">
          <span>返回结果</span>
          <el-tag :type="ok ? 'success' : 'danger'" size="small">{{ ok ? '成功' : '失败' }}</el-tag>
        </div>
      </template>
      <pre class="output">{{ resultText }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
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
  } catch (e) {
    ok.value = false
    result.value = { error: e.message }
  } finally {
    loading.value = false
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
  max-height: 420px;
  overflow: auto;
  white-space: pre-wrap;
}
</style>
