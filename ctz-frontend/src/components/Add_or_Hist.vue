<template>
  <button :class="['fab', position]" @click="toggle" :aria-pressed="isHistory" :title="isHistory ? 'Historial' : 'Agregar'">
    <transition name="fade">
      <img v-if="!isHistory" key="add" class="icon icon-add" src="/icon_add.png" alt="Agregar" />
      <img v-else key="hist" class="icon icon-hist" src="/icon_comeback.png" alt="Historial" />
    </transition>
  </button>
</template>

<script setup>
import { computed, defineProps, defineEmits } from 'vue'

const props = defineProps({
  initial: { type: String, default: 'add' }, // 'add' or 'hist'
  position: { type: String, default: 'right' } // 'left' or 'right'
})
const emit = defineEmits(['change', 'action'])

const isHistory = computed(() => props.initial === 'hist')

function toggle() {
  const action = isHistory.value ? 'hist' : 'add'
  emit('change', props.initial)
  emit('action', action)
}
</script>

<style scoped>
.fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1200;
  width: 64px;
  height: 64px;
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
  .fab { width: 58px; height: 58px; right: 14px; bottom: 14px; font-size: 26px; }
  .fab.left { left: 14px; }
  .icon { width: 34px; height: 34px; }
  .icon-add { width: 22px; height: 22px; }
}
</style>
