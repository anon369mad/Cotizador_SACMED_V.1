<template>
  <div class="preview-wrapper">
    <article class="preview-sheet">
      <header class="sheet-header">
        <img src="/sacmed.png" alt="logo" class="logo" />
        <div>
          <p class="doc-mark">Documento de cotización</p>
          <h3>Cotización Tipo {{ quote.planType || 'Período' }}</h3>
          <p class="meta">Ejecutivo: {{ quote.ejecutivo || 'Usuario' }}</p>
        </div>
      </header>

      <section class="sheet-section">
        <h4>Datos del cliente</h4>
        <div class="two-cols">
          <div>
            <span class="label">Cliente</span>
            <p>{{ quote.name || quote.cliente || '—' }}</p>
          </div>
          <div>
            <span class="label">RUT</span>
            <p>{{ quote.rut || '—' }}</p>
          </div>
        </div>
      </section>

      <section class="sheet-section" v-if="showMonths">
        <h4>Período de contratación</h4>
        <p class="period-text">{{ periodDescriptor }}</p>
      </section>

      <section class="sheet-section">
        <h4>Servicios</h4>
        <table class="items-table">
          <thead>
            <tr>
              <th>Cant.</th>
              <th>Servicio</th>
              <th>Unitario</th>
              <th>Desc.</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in normalizedItems" :key="item.id ?? index">
              <td>{{ item.qty }}</td>
              <td>{{ item.name || 'Servicio' }}</td>
              <td class="mono">{{ formatMoney(item.unitValue) }}</td>
              <td>{{ item.discountPct }}%</td>
              <td class="mono strong">{{ formatMoney(item.total) }}</td>
            </tr>
            <tr v-if="!normalizedItems.length">
              <td colspan="5" class="empty">No hay servicios agregados</td>
            </tr>
          </tbody>
        </table>

        <div class="totals">
          <div>
            <span>Subtotal</span>
            <strong class="mono">{{ formatMoney(subtotal) }}</strong>
          </div>
          <div>
            <span>IVA ({{ Number(ivaPct) % 1 === 0 ? Number(ivaPct).toFixed(0) : Number(ivaPct).toFixed(1) }}%)</span>
            <strong class="mono">{{ formatMoney(iva) }}</strong>
          </div>
          <div>
            <span>Total mensual</span>
            <strong class="mono">{{ formatMoney(monthlyTotal) }}</strong>
          </div>
          <div v-if="periodDiscountPct > 0">
            <span>Descuento período ({{ periodDiscountPct }}% sobre total del período)</span>
            <strong class="mono">-{{ formatMoney(periodDiscountAmount) }}</strong>
          </div>
          <div class="grand-total">
            <span>{{ periodTotalLabel }}</span>
            <strong class="mono">{{ formatMoney(periodTotal) }}</strong>
          </div>
        </div>
      </section>

      <section class="sheet-section">
        <h4>Condiciones</h4>
        <ul class="conditions-list" v-if="conditionEntries.length">
          <li v-for="(condition, index) in conditionEntries" :key="`${condition.text}-${index}`" class="condition-item">
            <span class="cond-source" :class="condition.source === 'service' ? 'service' : 'manual'">
              {{ conditionLabel(condition) }}
            </span>
            <span class="cond-text">{{ condition.text }}</span>
          </li>
        </ul>
        <p v-else class="empty">No hay condiciones registradas.</p>
      </section>


      <section class="sheet-section">
        <h4>Observaciones</h4>
        <ul class="conditions-list" v-if="observationEntries.length">
          <li v-for="(observation, index) in observationEntries" :key="`obs-${index}`" class="condition-item">
            <span class="cond-source manual">Observación</span>
            <span class="cond-text">{{ observation }}</span>
          </li>
        </ul>
        <p v-else class="empty">No hay observaciones registradas.</p>
      </section>

      <footer class="sheet-footer">
        Documento generado por: <strong>{{ quote.ejecutivo || 'Usuario' }}</strong>
      </footer>
    </article>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  quote: {
    type: Object,
    default: () => ({})
  }
})

const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const ivaPctFromDb = ref(null)

const isConfirmedQuote = computed(() =>
  String(props.quote?.estado || "").toUpperCase() === "CONFIRMADA"
)

const ivaPct = computed(() => Number(
  props.quote.iva_porcentaje
  ?? props.quote.porcentaje
  ?? ivaPctFromDb.value
  ?? 19
))

async function loadIvaPct() {
  try {
    const res = await fetch(`${apiBaseUrl}/iva`)
    if (!res.ok) return

    const list = await res.json()
    if (!Array.isArray(list) || !list.length) return

    const orderedIva = [...list].sort((a, b) => Number(b?.id_iva || 0) - Number(a?.id_iva || 0))

    let selected = null
    if (isConfirmedQuote.value && props.quote?.id_iva != null) {
      selected = orderedIva.find((entry) => Number(entry.id_iva) === Number(props.quote.id_iva))
    }

    if (!selected) selected = orderedIva.find((entry) => entry?.activo) || orderedIva[0]
    if (selected?.porcentaje != null) ivaPctFromDb.value = Number(selected.porcentaje)
  } catch (e) {
    // keep fallback
  }
}

onMounted(loadIvaPct)

watch(() => [props.quote?.id_iva, props.quote?.estado], loadIvaPct)

function normalizeConditionEntry(entry) {
  if (entry && typeof entry === 'object') {
    const text = String(entry.text ?? entry.condicion ?? '').trim()
    if (!text) return null
    return {
      text,
      source: entry.source === 'service' ? 'service' : 'manual',
      serviceName: entry.serviceName ?? null
    }
  }

  const text = String(entry || '').trim()
  if (!text) return null
  return {
    text,
    source: 'manual',
    serviceName: null
  }
}

const normalizedItems = computed(() => {
  return (props.quote.items || []).map((item, index) => {
    const qty = Number(item.qty ?? item.quantity ?? 0)
    const unitValue = Number(item.unitValue ?? item.value ?? 0)
    const discountPct = Number(item.discountPct ?? item.discount ?? 0)
    const total = Math.round(qty * unitValue * (1 - discountPct / 100))

    return {
      id: item.id ?? index,
      name: item.name,
      qty,
      unitValue,
      discountPct,
      total
    }
  })
})

const conditionEntries = computed(() => {
  const source = props.quote.condiciones ?? props.quote.conditions ?? []
  if (Array.isArray(source)) {
    return source
      .map((entry) => normalizeConditionEntry(entry))
      .filter(Boolean)
  }

  return String(source || '')
    .split(/\r?\n/)
    .map((line) => normalizeConditionEntry(line))
    .filter(Boolean)
})


const observationEntries = computed(() => {
  const source = props.quote.observaciones ?? props.quote.observations ?? []
  if (Array.isArray(source)) {
    return source
      .map((entry) => String(entry || '').trim())
      .filter(Boolean)
  }

  return String(source || '')
    .split(/\r?\n/)
    .map((line) => String(line || '').trim())
    .filter(Boolean)
})

const subtotal = computed(() => {
  const explicitSubtotal = Number(props.quote.subtotal)
  if (Number.isFinite(explicitSubtotal) && explicitSubtotal > 0) {
    return Math.round(explicitSubtotal)
  }

  return normalizedItems.value.reduce((sum, item) => sum + item.total, 0)
})

const historicalIvaPct = computed(() => {
  const pct = Number(props.quote.iva_porcentaje ?? props.quote.porcentaje)
  return Number.isFinite(pct) ? pct : null
})

const iva = computed(() => {
  if (isConfirmedQuote.value && historicalIvaPct.value != null) {
    return Math.round(subtotal.value * (historicalIvaPct.value / 100))
  }

  const explicitIva = Number(props.quote.ivaMonto ?? props.quote.iva_monto)
  if (Number.isFinite(explicitIva) && explicitIva > 0) {
    return Math.round(explicitIva)
  }

  return Math.round(subtotal.value * (Number(ivaPct.value || 19) / 100))
})

const isReducedConnectionPlan = computed(() => {
  const connections = Number(props.quote.conexiones ?? props.quote.connections ?? 0)
  return showMonths.value && (connections === 1 || connections === 2)
})

const periodMonthsForTotal = computed(() => {
  if (!showMonths.value) return 1
  if (isReducedConnectionPlan.value) return 3
  return Math.max(1, Number(props.quote.periodMonths ?? props.quote.periods ?? 1))
})

const monthlyTotal = computed(() => {
  const explicitMonthlyTotal = Number(props.quote.totalMensual ?? props.quote.total)
  if (Number.isFinite(explicitMonthlyTotal) && explicitMonthlyTotal > 0) {
    return Math.round(explicitMonthlyTotal)
  }
  return subtotal.value + iva.value
})

const periodDiscountPct = computed(() => {
  if (!showMonths.value) return 0
  const months = Math.max(1, Number(props.quote.periodMonths ?? props.quote.periods ?? 1))
  if (months >= 12) return 10
  if (months >= 6) return 5
  return 0
})

const basePeriodTotal = computed(() => {
  if (!showMonths.value) return monthlyTotal.value
  return Math.round(monthlyTotal.value * periodMonthsForTotal.value)
})

const periodDiscountAmount = computed(() => Math.round(basePeriodTotal.value * (periodDiscountPct.value / 100)))

const periodTotal = computed(() => {
  const explicitTotal = Number(
    props.quote.totalHistorial ?? props.quote.total_historial ?? props.quote.price
  )
  if (Number.isFinite(explicitTotal) && explicitTotal > 0) {
    return Math.round(explicitTotal)
  }

  if (!showMonths.value) return monthlyTotal.value
  return Math.round(basePeriodTotal.value - periodDiscountAmount.value)
})

const periodTotalLabel = computed(() => {
  if (!showMonths.value) return 'Total'
  const months = Math.max(1, Number(props.quote.periodMonths ?? props.quote.periods ?? 1))
  const label = months === 3 ? 'Total trimestral' : `Total (Cada ${months} mes${months === 1 ? '' : 'es'})`
  if (periodDiscountPct.value > 0) return `${label} con descuento`
  return label
})

const showMonths = computed(() => {
  const planType = String(props.quote.planType || '').toLowerCase()
  return planType.includes('período') || planType.includes('periodo')
})

const periodDescriptor = computed(() => {
  const months = Math.max(1, Number(props.quote.periodMonths ?? props.quote.periods ?? 1))
  const discountText = periodDiscountPct.value > 0 ? ` (descuento ${periodDiscountPct.value}% sobre total del período)` : ''
  return `${months} mes${months === 1 ? '' : 'es'}${discountText}`
})

function formatMoney(value) {
  return '$' + Number(value || 0).toLocaleString('es-CL')
}

function conditionLabel(condition) {
  if (condition.source !== 'service') return 'Manual'
  return condition.serviceName ? `Servicio: ${condition.serviceName}` : 'Servicio asociado'
}
</script>

<style scoped>
.preview-wrapper {
  width: 100%;
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.preview-sheet {
  width: 100%;
  background: #fff;
  border: 1px solid #d6dde7;
  box-shadow: 0 10px 25px rgba(15, 21, 64, 0.08);
  border-radius: 4px;
  padding: 22px 22px 16px;
  color: #0f172a;
}

.sheet-header {
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #dbe2ec;
  padding-bottom: 12px;
}

.logo {
  width: 58px;
  height: auto;
}

.doc-mark {
  margin: 0;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
}

.sheet-header h3 {
  margin: 2px 0 4px;
  font-size: 15px;
}

.meta {
  margin: 0;
  color: #475569;
  font-size: 12px;
}

.sheet-section {
  margin-top: 16px;
}

.sheet-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #0f172a;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.period-text {
  margin: 0;
  font-size: 13px;
  color: #334155;
}

.two-cols {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.two-cols p {
  margin: 2px 0 0;
  font-size: 13px;
}

.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.items-table th,
.items-table td {
  padding: 9px 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  text-align: left;
}

.items-table th {
  background: #edf2f7;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 11px;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.strong {
  font-weight: 700;
}

.empty {
  color: #64748b;
  font-style: italic;
}

.totals {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #d9e1eb;
  background: #f8fafc;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.totals div {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.grand-total {
  border-top: 1px dashed rgba(0, 0, 0, 0.2);
  padding-top: 8px;
  font-weight: 700;
}

.conditions-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-item {
  display: grid;
  grid-template-columns: minmax(160px, auto) 1fr;
  gap: 8px;
  align-items: center;
}

.cond-source {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.cond-source.service {
  background: rgba(37, 99, 235, 0.14);
  color: #1e40af;
}

.cond-source.manual {
  background: rgba(22, 163, 74, 0.14);
  color: #166534;
}

.cond-text {
  font-size: 13px;
  color: #334155;
}

.sheet-footer {
  margin-top: 16px;
  padding-top: 10px;
  border-top: 1px solid #dbe2ec;
  font-size: 12px;
  color: #475569;
}

@media (max-width: 720px) {
  .preview-sheet {
    padding: 16px;
  }

  .two-cols,
  .condition-item {
    grid-template-columns: 1fr;
  }
}
</style>
