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
      <Login />
    </div>
  </div>
</template>

<style>
.app-wrapper {
  position: relative;
  width: 100%;
  display: flex;
  flex-direction: row;
}

.logo-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
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
  /* smoother, continuous animation */
  animation: sweep 4s linear infinite;
}

.logo {
  height: 300px;
  width: auto;
  object-fit: contain;
  display: block;
}

@keyframes sweep {
  0% { transform: translateX(-150%); }
  100% { transform: translateX(250%); }
}
</style>