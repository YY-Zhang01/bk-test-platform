<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-head">
        <span>历史报告</span>
        <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
      </div>
    </template>

    <el-table :data="reports" size="default" stripe>
      <el-table-column prop="name" label="报告文件" min-width="230">
        <template #default="{ row }">
          <span class="mono">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="mtime" label="生成时间" width="150" />
      <el-table-column label="通过率" width="140" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.rate !== undefined" :type="rateType(row)" size="small">
            {{ Math.round((row.rate || 0) * 100) }}%
          </el-tag>
          <span v-else class="na">-</span>
        </template>
      </el-table-column>
      <el-table-column label="通过 / 失败 / 跳过" width="180" align="center">
        <template #default="{ row }">
          <span v-if="row.passed !== undefined" class="counts">
            <span class="c-passed">{{ row.passed }}</span> /
            <span class="c-failed">{{ row.failed }}</span> /
            <span class="c-skipped">{{ row.skipped }}</span>
          </span>
          <span v-else class="na">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" type="primary" text @click="openReport(row.url)">打开</el-button>
          <el-button size="small" type="danger" text @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!reports.length" description="还没有报告，先去「跑测试」跑一次全量" />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api'

const reports = ref([])

function rateType(row) {
  if ((row.failed || 0) > 0) return 'danger'
  if ((row.skipped || 0) > 0) return 'warning'
  return 'success'
}

async function load() {
  try {
    reports.value = await api.reports()
  } catch (e) {
    console.error(e)
  }
}

function openReport(url) {
  window.open(url, '_blank')
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除 ${row.name}？`, '删除报告', { type: 'warning' })
  } catch { return }
  try {
    await api.deleteReport(row.name)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mono {
  font-family: Consolas, monospace;
  font-size: 13px;
}
.na {
  color: #cbd5e1;
}
.counts {
  font-family: Consolas, monospace;
  font-size: 12px;
}
.c-passed { color: #10b981; }
.c-failed { color: #ef4444; }
.c-skipped { color: #f59e0b; }
</style>
