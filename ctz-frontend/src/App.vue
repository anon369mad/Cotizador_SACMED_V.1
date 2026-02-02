<script setup>
import { ref } from 'vue'
import Logo from './components/Logo.vue'
import Home from './components/Home.vue'

const loggedIn = ref(false)
</script>

<template>
  <Logo v-if="!loggedIn" @login-ok="loggedIn = true" />
  <Home v-else />
</template>

<style>
* {
  margin: 0;
  padding: 0; 
}

body,
html,
#app {
  background: white;
  height: 100%;
  margin: 0;
  padding: 0;
  width: 100%;
}
</style>
