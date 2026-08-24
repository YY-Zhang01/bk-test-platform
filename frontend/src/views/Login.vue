<template>
  <div class="login-page">
    <div class="orb orb1"></div>
    <div class="orb orb2"></div>
    <div class="orb orb3"></div>

    <div class="login-card">
      <div class="logo-mark">
        <el-icon :size="26" color="#fff"><Odometer /></el-icon>
      </div>
      <h1 class="title">蓝鲸测试平台</h1>
      <p class="subtitle">CMDB × JOB 双系统全方位测试</p>

      <div class="form">
        <el-input
          v-model="username"
          size="large"
          placeholder="账号"
          :prefix-icon="User"
        />
        <el-input
          v-model="password"
          type="password"
          size="large"
          placeholder="密码"
          show-password
          :prefix-icon="Lock"
          @keyup.enter="doLogin"
        />
        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="doLogin"
        >
          登 录
        </el-button>
      </div>

      <p v-if="error" class="error">
        <el-icon><WarningFilled /></el-icon> {{ error }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Lock, User, WarningFilled } from '@element-plus/icons-vue'
import { api, setToken } from '@/api'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function doLogin() {
  if (!username.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const r = await api.login(username.value, password.value)
    if (r.ok && r.token) {
      setToken(r.token)
      router.push('/overview')
    }
  } catch (e) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0b1437 0%, #16134d 50%, #1e1b4b 100%);
  overflow: hidden;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}
.orb1 {
  width: 380px; height: 380px;
  background: #3b82f6;
  top: -80px; left: -60px;
}
.orb2 {
  width: 320px; height: 320px;
  background: #8b5cf6;
  bottom: -60px; right: -40px;
}
.orb3 {
  width: 220px; height: 220px;
  background: #0ea5e9;
  top: 40%; right: 15%;
  opacity: 0.35;
}
.login-card {
  position: relative;
  z-index: 1;
  width: 380px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 20px;
  backdrop-filter: blur(20px);
  padding: 40px 36px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
}
.logo-mark {
  width: 56px; height: 56px;
  margin: 0 auto 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.5);
}
.title {
  margin: 0;
  color: #fff;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1px;
}
.subtitle {
  margin: 8px 0 28px;
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.form :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.2) inset;
  border-radius: 10px;
}
.form :deep(.el-input__inner) {
  color: #fff;
}
.form :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.4);
}
.login-btn {
  height: 46px;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
}
.login-btn:hover {
  opacity: 0.92;
}
.error {
  margin: 16px 0 0;
  color: #fca5a5;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
</style>
