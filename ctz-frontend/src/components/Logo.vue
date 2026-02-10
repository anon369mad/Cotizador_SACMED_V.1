<script setup>
    import Login from './Login.vue'
</script>
<template>
  <div class="app-wrapper">
    <div class="logo-section">
      <div class="logo-wrap">
        <img src="/sacmed.png" alt="SACMED Logo" class="logo">
      </div>
    </div>
    <div class="login-section">
      <Login @login-ok="(u) => $emit('login-ok', u)" />
    </div>
  </div>
</template>

<style scoped>
.app-wrapper {
  width: 100%;
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(320px, 1fr);
  gap: clamp(20px, 3vw, 40px);
  padding: clamp(20px, 4vw, 48px);
  align-items: center;
}

.logo-section,
.login-section {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-wrap {
  position: relative;
  overflow: hidden;
  display: inline-block;
}

.logo-wrap::after {
  content: '';
  position: absolute;
  top: -20%;
  left: 0;
  width: 30%;
  height: 140%;
  background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.95) 50%, rgba(255,255,255,0) 100%);
  transform: translateX(-150%);
  filter: blur(10px);
  opacity: 0.9;
  pointer-events: none;
  animation: sweep 4s linear infinite;
}

.logo {
  width: min(100%, 460px);
  max-height: clamp(120px, 26vw, 300px);
  object-fit: contain;
}

@keyframes sweep {
  0% { transform: translateX(-150%); }
  100% { transform: translateX(250%); }
}

@media (max-width: 900px) {
  .app-wrapper {
    grid-template-columns: 1fr;
    place-items: center;
    gap: 12px;
  }

  .logo {
    max-height: 170px;
  }

  .logo-section {
    padding-top: 10px;
  }
}
</style>
