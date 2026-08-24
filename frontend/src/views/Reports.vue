<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-head">
        <span>历史报告</span>
        <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
      </div>
    </template>

    <el-table :data="reports" size="default" stripe>
      <el-table-column prop="name" label="报告文件" min-width="260">
        <template #default="{ row }">
          <span class="mono">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="mtime" label="生成时间" width="160" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" type="primary" text @click="openReport(row.url)">
            打开
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!reports.length" description="还没有报告，先去「跑测试」跑一次全量" />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '@/api'

const reports = ref([])

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
</style>
