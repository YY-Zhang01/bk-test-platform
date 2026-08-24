<template>
  <div>
    <el-card shadow="never" class="toolbar">
      <div class="toolbar-inner">
        <div class="counts">
          <span class="count-num">{{ total }}</span> 个用例 ·
          <span class="count-num">{{ functions }}</span> 个函数
        </div>
        <div class="filters">
          <el-input
            v-model="keyword"
            placeholder="搜索用例名 / 作用"
            clearable
            style="width: 240px"
            :prefix-icon="Search"
          />
          <el-radio-group v-model="envFilter" size="default">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="否">可跑</el-radio-button>
            <el-radio-button label="是">等账号</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </el-card>

    <el-collapse v-model="openGroups" style="margin-top: 16px">
      <el-collapse-item v-for="g in filteredGroups" :key="g.group" :name="g.group">
        <template #title>
          <span class="group-title">{{ g.group }}</span>
          <el-tag size="small" type="info" class="group-count">{{ g.cases.length }}</el-tag>
        </template>
        <el-table :data="g.cases" size="small" stripe>
          <el-table-column label="用例" min-width="260">
            <template #default="{ row }">
              <div class="case-name">{{ row.name }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="desc" label="作用 / 设计原因" min-width="340" show-overflow-tooltip />
          <el-table-column prop="marker" label="marker" width="140">
            <template #default="{ row }">
              <span class="mono">{{ row.marker || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.env === '否' ? 'success' : 'warning'" size="small">
                {{ row.env === '否' ? '可跑' : '等账号' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { api } from '@/api'

const total = ref('-')
const functions = ref('-')
const groups = ref([])
const keyword = ref('')
const envFilter = ref('all')
const openGroups = ref([])

const filteredGroups = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return groups.value
    .map((g) => {
      const cases = g.cases.filter((c) => {
        const matchKw = !kw || c.name.toLowerCase().includes(kw) || (c.desc || '').toLowerCase().includes(kw)
        const matchEnv = envFilter.value === 'all' || c.env === envFilter.value
        return matchKw && matchEnv
      })
      return { ...g, cases }
    })
    .filter((g) => g.cases.length > 0)
})

onMounted(async () => {
  try {
    const data = await api.cases()
    total.value = data.total
    functions.value = data.functions
    groups.value = data.groups || []
    openGroups.value = (data.groups || []).map((g) => g.group)
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.toolbar-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.counts {
  font-size: 14px;
  color: #606266;
}
.count-num {
  font-size: 20px;
  font-weight: 700;
  color: #3b82f6;
}
.filters {
  display: flex;
  gap: 12px;
  align-items: center;
}
.group-title {
  font-weight: 600;
}
.group-count {
  margin-left: 10px;
}
.case-name {
  font-weight: 500;
}
.mono {
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #909399;
}
</style>
