<script setup>
import { ref, onMounted } from 'vue'
import Logo from './components/Logo.vue'
import Home from './components/Home.vue'
import AdminPanel from './components/Admin_Panel.vue'

const loggedIn = ref(false)
const userName = ref('')
const userId = ref(null)
const userRole = ref('')

function handleLogin(usuario) {
  userName.value = usuario.nombre || usuario.email || 'Usuario'
  userId.value = usuario.id_usuario ?? null
  userRole.value = usuario.rol || ''
  loggedIn.value = true
}

function handleLogout() {
  loggedIn.value = false
  userName.value = ''
  userId.value = null
  userRole.value = ''
  localStorage.clear()
}

onMounted(() => {
  window.addEventListener('logout', handleLogout)
})

</script>

<template>
  <Logo v-if="!loggedIn" @login-ok="handleLogin" />
  <AdminPanel
    v-else-if="String(userRole).toUpperCase() === 'ADMIN'"
    :userName="userName"
    :userId="userId"
    :userRole="userRole"
  />
  <Home v-else :userName="userName" :userId="userId" @logout="handleLogout" />
</template>

<style>
#app {
  min-height: 100vh;
  width: 100%;
}
</style>
