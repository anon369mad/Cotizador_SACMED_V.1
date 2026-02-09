<script setup>
import { computed, ref } from 'vue'
const emit = defineEmits(['discard'])

const props = defineProps({
  baseData: {
    type: Object,
    required: true
  }
})

const items = computed(() => props.baseData.items || [])

const subtotal = computed(() =>
  items.value.reduce(
    (s, it) => s + it.qty * it.unitValue * (1 - it.discountPct / 100),
    0
  )
)

const iva = computed(() => Math.round(subtotal.value * 0.19))
const total = computed(() => subtotal.value + iva.value)
const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

function rowTotal(it) {
  return it.qty * it.unitValue * (1 - it.discountPct / 100)
}

function editItem(it) {
  // luego lo conectas con modal o evento
  console.log('editar', it)
}

function removeItem(id) {
  const idx = props.baseData.items.findIndex(i => i.id === id)
  if (idx !== -1) props.baseData.items.splice(idx, 1)
}
async function confirmQuote() {
  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const payload = {
      tipo: props.baseData.planType === 'Única' ? 'UNICA' : 'PERIODO',
      id_cliente: Number(props.baseData.idCliente ?? 1),
      id_usuario: Number(props.baseData.idUsuario ?? 1),
      id_iva: Number(props.baseData.idIva ?? 1),
      meses: props.baseData.planType === 'Única' ? null : props.baseData.periodMonths,
      conexiones: props.baseData.conexiones ?? 0,
      condiciones_adicionales: props.baseData.condiciones || null
    }

    const headerResponse = await fetch(`${apiBaseUrl}/cotizaciones`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!headerResponse.ok) {
      throw new Error('No se pudo crear la cotización')
    }

    const headerData = await headerResponse.json()
    const idCotizacion = headerData?.id_cotizacion
    if (!idCotizacion) {
      throw new Error('La respuesta no incluyó el id de cotización')
    }

    for (const item of props.baseData.items || []) {
      const detailPayload = {
        id_cotizacion: idCotizacion,
        id_prestacion: item.id_prestacion ?? null,
        descripcion_manual: item.name ?? null,
        cantidad: item.qty,
        valor_unitario: item.unitValue,
        descuento: item.discountPct ?? 0
      }

      const detailResponse = await fetch(`${apiBaseUrl}/cotizacion_detalles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(detailPayload)
      })

      if (!detailResponse.ok) {
        throw new Error(`No se pudo crear el detalle ${item.name || ''}`.trim())
      }
    }

    if (props.baseData.confirmOnSave) {
      const statusResponse = await fetch(`${apiBaseUrl}/cotizaciones/${idCotizacion}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ estado: 'CONFIRMADA' })
      })

      if (!statusResponse.ok) {
        throw new Error('No se pudo confirmar el estado de la cotización')
      }
    }

    successMessage.value = 'Cotización confirmada y guardada correctamente.'
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Ocurrió un error inesperado al confirmar la cotización'
  } finally {
    isSaving.value = false
  }
}

function discardQuote() {
  emit('discard')
}

</script>


<template>
<section class="preview">

  <header >
    <h4 class="tipo">Cotización Tipo {{ baseData.planType }}</h4>
    <h4 class="client">{{ baseData.cliente || '—' }}</h4>
    <small class="client">{{ baseData.rut }}</small>
  </header>

  <!-- TABLA -->
  <table class="services-table">
    <thead>
      <tr>
        <th>Cant.</th>
        <th>Servicio</th>
        <th>Unitario</th>
        <th>Desc.</th>
        <th>Total</th>
        <th></th>
      </tr>
    </thead>

   <tbody>

  <!-- FILA CONFIGURACIÓN DEL SERVICIO -->
  <tr class="config-row">
    <td>1</td>
    <td>
      <strong></strong>
        <span v-if="baseData.planType !== 'Única'">
          {{ baseData.periodMonths }} meses,
          {{ baseData.conexiones }} conexiones
        </span>
    </td>
    <td>—</td>
    <td>—</td>
    <td class="bold">—</td>
    <td class="actions">
      <button @click="editItem(baseData)">✏️</button>
      <button @click="removeItem(null)">🗑️</button>
    </td>
  </tr>

  <!-- ITEMS -->
  <tr v-for="it in items" :key="it.id">
    <td>{{ it.qty }}</td>
    <td>{{ it.name }}</td>
    <td>${{ it.unitValue }}</td>
    <td>{{ it.discountPct }}%</td>
    <td class="bold">${{ rowTotal(it).toFixed(0) }}</td>
    <td class="actions">
      <button @click="editItem(it)">✏️</button>
      <button @click="removeItem(it.id)">🗑️</button>
    </td>
  </tr>

  <tr v-if="!items.length">
    <td colspan="6" class="empty">
      No hay servicios agregados
    </td>
  </tr>

</tbody>

  </table>

  <!-- TOTALES -->
  <div class="totals">
    <div>
      <span>Subtotal</span>
      <strong>${{ subtotal.toFixed(0) }}</strong>
    </div>
    <div>
      <span>IVA (19%)</span>
      <strong>${{ iva.toFixed(0) }}</strong>
    </div>
    <div class="grand-total">
      <span>Total mensual</span>
      <strong>${{ total.toFixed(0) }}</strong>
    </div>
  </div>

</section>
<div class="final-actions">
  <button class="btn-discard" @click="discardQuote">
    Descartar
  </button>

  <button class="btn-confirm" :disabled="isSaving" @click="confirmQuote">
    {{ isSaving ? 'Guardando...' : 'Confirmar cotización' }}
  </button>
</div>
<p v-if="errorMessage" class="status-message error">{{ errorMessage }}</p>
<p v-if="successMessage" class="status-message success">{{ successMessage }}</p>
</template>

<style scoped>
/* === TABLA GENERAL === */
.services-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: white;
  overflow: hidden;
}

.services-table th {
  font-weight: 600;
  background: #f1f5f9;
  color: #0f172a;
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: 0.04em;
}

.services-table th,
.services-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  text-align: left;
  vertical-align: middle;
}

/* === FILA CONFIGURACIÓN === */
.config-row {
  background: linear-gradient(90deg, #f8fafc, #f1f5f9);
  font-size: 12.5px;
}

.config-row td {
  color: #334155;
}

.config-row td:nth-child(2) {
  font-weight: 500;
}

.config-row .actions button {
  opacity: 0.6;
}

.config-row .actions button:hover {
  opacity: 1;
}

/* === ITEMS === */
.services-table tbody tr:not(.config-row):hover {
  background: #f8fafc;
}

.bold {
  font-weight: 600;
  color: #0f172a;
}

.status-message {
  margin-top: 12px;
  font-size: 13px;
}

.status-message.error {
  color: #b91c1c;
}

.status-message.success {
  color: #15803d;
}

/* === BOTONES === */
.actions button {
  background: none;
  border: none;
  cursor: pointer;
  margin-right: 6px;
  font-size: 14px;
  opacity: 0.7;
  transition: opacity 0.2s ease, transform 0.15s ease;
}

.actions button:hover {
  opacity: 1;
  transform: scale(1.1);
}

/* === EMPTY STATE === */
.empty {
  text-align: center;
  padding: 20px;
  color: #64748b;
  font-style: italic;
}

/* === TOTALES === */
.totals {
  margin-top: 18px;
  padding: 14px;
  background: #f8fafc;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.totals div {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #334155;
}

.grand-total {
  border-top: 1px dashed rgba(0,0,0,0.15);
  padding-top: 10px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}
.tipo {
  font-size: 11px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.client{
    color: #000000;
    font-weight: 600;
}
/* === BOTONES FINALES === */
.final-actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.final-actions button {
  padding: 9px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
}

/* DESCARTAR */
.btn-discard {
  background: #e2e8f0;
  color: #334155;
}

.btn-discard:hover {
  background: #cbd5e1;
}

/* CONFIRMAR */
.btn-confirm {
  background: #38bdf8;
  color: white;
}

.btn-confirm:hover {
  background: #0ea5e9;
}

</style>
