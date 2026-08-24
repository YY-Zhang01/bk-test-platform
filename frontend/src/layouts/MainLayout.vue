<template>
  <el-container class="layout">
    <el-aside width="208px" class="aside">
      <div class="logo">
        <span class="logo-mark">蓝</span>
        <span class="logo-text">蓝鲸测试平台</span>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="menu"
        background-color="#0b1437"
        text-color="rgba(255,255,255,.7)"
        active-text-color="#ffffff"
      >
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="header-title">{{ $route.meta.title }}</span>
        <el-tag type="success" effect="light" size="small">在线</el-tag>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
const menus = [
  { path: '/overview', title: '总览', icon: 'Odometer' },
  { path: '/run', title: '跑测试', icon: 'VideoPlay' },
  { path: '/probe', title: '接口调试', icon: 'Connection' },
  { path: '/reports', title: '报告', icon: 'Document' },
  { path: '/gen', title: 'AI 生成', icon: 'MagicStick' },
  { path: '/cases', title: '用例库', icon: 'List' },
  { path: '/ui', title: 'UI 自动化', icon: 'Monitor' },
]
</script>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  background: #0b1437;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  color: #fff;
}

.logo-mark {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}

.logo-text {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
}

.menu {
  border-right: none;
  flex: 1;
}

.menu :deep(.el-menu-item) {
  height: 48px;
  margin: 2px 8px;
  border-radius: 6px;
}

.menu :deep(.el-menu-item.is-active) {
  background: #3b82f6;
}

.menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
}

.header {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
}

.main {
  padding: 20px;
  overflow-y: auto;
}
</style>
