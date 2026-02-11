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
  idUsuario: null,
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
  idUsuario: null,
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
    idUsuario: quote.idUsuario ?? quote.id_usuario ?? base.idUsuario ?? null,
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
  <section class="quote-workspace">
    <div class="form-cotizador">
      <Cotizador
        :key="`${tabId}-${resetKey}`"
        :tab-id="tabId"
        :initial-data="initialData"
        @update-preview="updatePreview"
      />
    </div>

    <div class="right-panel">
      <div class="card-header">
        <h4>Previsualización</h4>
        <small>Formato de documento formal</small>
      </div>
      <div class="preview-card">
        <Editable_Preview
          :baseData="previewData"
          @discard="resetAll"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>

.quote-workspace {
  display: grid;
  grid-template-columns: minmax(430px, 1.1fr) minmax(430px, 1fr);
  gap: clamp(18px, 2vw, 30px);
  align-items: start;
  justify-items: stretch;
  width: auto;
  max-width: min(1440px, calc(100% - clamp(24px, 4vw, 48px)));
  margin: 0 auto;
  padding: 0 clamp(12px, 2vw, 24px);
}

.card-header {
  padding: 14px 18px;
  border-bottom: 1px solid rgba(15, 21, 64, 0.08);
  color: #1f2b3a;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.card-header h4 {
  font-weight: 600;
  margin: 0;
}

.card-header small {
  color: #6b747a;
}

.form-cotizador {
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.right-panel {
  border: 1px solid rgba(15, 21, 64, 0.12);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 10px;
  background: #f5f7fb;
  width: max-content;
  border-radius: 14px;
  box-shadow: 0 10px 24px rgba(15, 21, 64, 0.06);
}

.preview-card {
  background: white;
  border-top: 1px solid rgba(15, 21, 64, 0.06);
  width: 100%;
  border-radius: 0 0 14px 14px;
  padding: 18px;
}

@media (max-width: 1180px) {
  .quote-workspace {
    grid-template-columns: 1fr;
    max-width: min(920px, calc(100% - clamp(24px, 4vw, 48px)));
  }
}

</style>
