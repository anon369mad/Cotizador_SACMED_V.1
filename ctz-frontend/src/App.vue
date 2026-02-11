<script setup>
import { ref, onMounted } from 'vue'
import Logo from './components/Logo.vue'
import Home from './components/Home.vue'

const loggedIn = ref(false)
const userName = ref('')
const userId = ref(null)

function handleLogin(usuario) {
  userName.value = usuario.nombre || usuario.email || 'Usuario'
  userId.value = usuario.id_usuario ?? null
  loggedIn.value = true
}

function handleLogout() {
  loggedIn.value = false
  userName.value = ''
  userId.value = null
  localStorage.clear()
}

onMounted(() => {
  window.addEventListener('logout', handleLogout)
})

</script>

<template>
  <Logo v-if="!loggedIn" @login-ok="handleLogin" />
  <Home v-else :userName="userName" :userId="userId" @logout="handleLogout" />
</template>

<style>
#app {
  min-height: 100vh;
  width: 100%;
}
</style>
