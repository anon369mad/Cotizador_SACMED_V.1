<script setup>
import { ref, onMounted } from 'vue'
import Logo from './components/Logo.vue'
import Home from './components/Home.vue'

const loggedIn = ref(false)
const userName = ref('')

function handleLogin(usuario) {
  userName.value = usuario.nombre || usuario.email || 'Usuario'
  loggedIn.value = true
}

function handleLogout() {
  loggedIn.value = false
  userName.value = ''
  localStorage.clear()
}

onMounted(() => {
  window.addEventListener('logout', handleLogout)
})

</script>

<template>
  <Logo v-if="!loggedIn" @login-ok="handleLogin" />
  <Home v-else :userName="userName" @logout="handleLogout" />
</template>

<style>
#app {
  min-height: 100vh;
  width: 100%;
}
</style>
