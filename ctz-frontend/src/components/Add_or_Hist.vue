<template>
  <button :class="['fab', position]" @click="toggle" :aria-pressed="isHistory" :title="isHistory ? 'Historial' : 'Agregar'">
    <transition name="fade">
      <img v-if="!isHistory" key="add" class="icon icon-add" src="/icon_add.png" alt="Agregar" />
      <img v-else key="hist" class="icon icon-hist" src="/icon_comeback.png" alt="Historial" />
    </transition>
  </button>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue'

const props = defineProps({
  initial: { type: String, default: 'add' }, // 'add' or 'hist'
  position: { type: String, default: 'right' } // 'left' or 'right'
})
const emit = defineEmits(['change', 'action'])

const isHistory = ref(props.initial === 'hist')

function toggle() {
  const action = isHistory.value ? 'hist' : 'add' // action corresponding to the icon clicked
  isHistory.value = !isHistory.value
  emit('change', isHistory.value ? 'hist' : 'add')
  emit('action', action)
}

// react to prop changes if parent changes initial
watch(() => props.initial, (v) => {
  isHistory.value = v === 'hist'
})
</script>

<style scoped>
.fab {
  position: fixed;
  right: 28px;
  bottom: 28px;
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: linear-gradient(180deg, #1ca4ff, #0073ff);
  color: white;
  border: none;
  box-shadow: 0 14px 36px rgba(2, 22, 66, 0.22);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.fab.left { left: 28px; right: auto; }
.fab.right { right: 28px; left: auto; }
.fab:active { transform: scale(0.96); }

.icon {
  width: 48px;
  height: 48px;
  display: inline-block;
  line-height: 1;
  object-fit: contain;
}

/* make add icon slightly smaller */
.icon-add {
  width: 28px; /* smaller add icon */
  height: 28px;
  object-fit: contain;
}

/* mobile tweak for add icon */
@media (max-width: 480px) {
  .icon-add { width: 22px; height: 22px; }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(6px); }

/* small responsive tweak */
@media (max-width: 480px) {
  .fab { width: 76px; height: 76px; right: 18px; bottom: 18px; font-size: 32px; }
  .icon { width: 40px; height: 40px; }
  .icon-add { width: 28px; height: 28px; }
}
</style>
