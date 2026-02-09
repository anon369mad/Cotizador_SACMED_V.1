<script setup>
import { reactive, ref, watch, computed } from 'vue'
import Cotizador from './Cotizador.vue'
import Editable_Preview from './Editable_Preview.vue'

const props = defineProps({
  tabId: {
    type: [String, Number],
    required: true
  },
  quote: {
    type: Object,
    default: null
  }
})

const resetKey = ref(0)

const previewData = reactive({
  ejecutivo: '',
  cliente: '',
  rut: '',
  planType: 'Período',
  conexiones: 0,
  periodMonths: 0,
  condiciones: '',
  items: []
})

const defaultPreview = () => ({
  ejecutivo: '',
  cliente: '',
  rut: '',
  planType: 'Período',
  conexiones: 0,
  periodMonths: 0,
  condiciones: '',
  items: []
})

function normalizeQuote(quote) {
  const base = defaultPreview()
  if (!quote) return base

  const mapped = {
    ...quote,
    ejecutivo: quote.ejecutivo ?? quote.user ?? base.ejecutivo,
    cliente: quote.cliente ?? quote.name ?? base.cliente,
    conexiones: quote.conexiones ?? quote.connections ?? base.conexiones,
    condiciones: quote.condiciones ?? quote.conditions ?? base.condiciones
  }

  return {
    ...base,
    ...mapped,
    items: JSON.parse(JSON.stringify(mapped.items || base.items))
  }
}

const initialData = computed(() => normalizeQuote(props.quote))

watch(
  () => props.quote,
  (value) => {
    Object.assign(previewData, normalizeQuote(value))
  },
  { immediate: true }
)

function updatePreview(data) {
  Object.assign(previewData, data)
}
function resetAll() {
  // Reset preview
  Object.assign(previewData, defaultPreview())

  // Avisar al Cotizador (opcional)
  localStorage.removeItem(`cotizador_form_${props.tabId}`)
  resetKey.value++
}

</script>

<template>
    <div class="form-cotizador">
  <!-- IZQUIERDA -->
  <Cotizador
  :key="`${tabId}-${resetKey}`"
  :tab-id="tabId"
  :initial-data="initialData"
  @update-preview="updatePreview"
  />
    </div>

  <!-- DERECHA -->
    <div class="right-panel">
         <div class="card-header">
           <h4>Resumen</h4>
         </div>
      <div class="preview-card">
        <Editable_Preview
        :baseData="previewData"
        @discard="resetAll"
        />
      </div>
    </div>
</template>

<style scoped>

.card-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(15, 21, 64, 0.08);
  color: black;
}
.card-header h4 {
  font-weight: 600;
}

.form-cotizador {
  display: flex;
  justify-content: center;
  align-items: start;
}

/* Card derecha */
.right-panel {
  border: rgba(0, 0, 0, 0.26) solid 1px;
  display: flex;
  flex-direction: column;
  align-items: start;
  padding: 12px;
  background: #0000000a;
  width: 100%;
  height: 100%;
  border-radius: 0px;
}

.preview-card {
  background: white;
  border: rgba(0, 0, 0, 0.26) solid 1px;
  box-shadow: 0 8px 20px rgba(12, 38, 70, 0.05);
  width: 100%;
  height: 100%;
  border-radius: 10px;
}

</style>
