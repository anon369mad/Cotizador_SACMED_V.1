<script setup>
import { reactive } from 'vue'
import Cotizador from './Cotizador.vue'
import Editable_Preview from './Editable_Preview.vue'

const previewData = reactive({
  ejecutivo: '',
  cliente: '',
  rut: '',
  conexiones: 0,
  periodMonths: 0,
  items: [],
  subtotal: 0,
  iva: 0,
  total: 0
})
defineProps({
  tabId: {
    type: [String, Number],
    required: true
  }
})
function updatePreview(data) {
  Object.assign(previewData, data)
}
function resetAll() {
  // Reset preview
  previewData.ejecutivo = ''
  previewData.cliente = ''
  previewData.rut = ''
  previewData.conexiones = 0
  previewData.periodMonths = 0
  previewData.items = []
  previewData.subtotal = 0
  previewData.iva = 0
  previewData.total = 0

  // Avisar al Cotizador (opcional)
  resetKey.value++
}

</script>

<template>
    <div class="form-cotizador">
  <!-- IZQUIERDA -->
  <Cotizador
  :tab-id="tabId"
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
