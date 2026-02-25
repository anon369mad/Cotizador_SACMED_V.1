<script setup>
import { computed, ref, onMounted } from 'vue'
const emit = defineEmits(['discard', 'sync-form', 'quote-saved', 'history-changed', 'quote-finalized', 'back'])

const props = defineProps({
  baseData: {
    type: Object,
    required: true
  }
})

const items = computed(() => props.baseData.items || [])

function normalizeConditionEntry(entry) {
  if (entry && typeof entry === 'object') {
    const text = String(entry.text ?? entry.condicion ?? '').trim()
    if (!text) return null
    return {
      text,
      source: entry.source === 'service' ? 'service' : 'manual',
      itemId: entry.itemId ?? null,
      serviceName: entry.serviceName ?? null
    }
  }

  const text = String(entry || '').trim()
  if (!text) return null
  return {
    text,
    source: 'manual',
    itemId: null,
    serviceName: null
  }
}

const conditionsList = computed(() => {
  const c = props.baseData.condiciones ?? props.baseData.condiciones_adicionales ?? null
  if (!c) return []
  if (Array.isArray(c)) {
    return c
      .map((entry) => normalizeConditionEntry(entry))
      .filter(Boolean)
  }
  return String(c)
    .split(/\r?\n/)
    .map((entry) => normalizeConditionEntry(entry))
    .filter(Boolean)
})


const observationsList = computed(() => {
  const source = props.baseData.observaciones ?? props.baseData.observaciones_adicionales ?? []
  if (Array.isArray(source)) {
    return source
      .map((entry) => String(entry || '').trim())
      .filter(Boolean)
  }
  return String(source || '')
    .split(/\r?\n/)
    .map((entry) => String(entry || '').trim())
    .filter(Boolean)
})

const editIndex = ref(-1)
const editText = ref('')
const editItemId = ref(null)
const editQty = ref(1)
const editDiscount = ref(0)
const editUnitValue = ref(0)
const editCurrency = ref('CLP')

function ensureConditionsArray() {
  if (!props.baseData.condiciones) {
    props.baseData.condiciones = []
    return
  }
  if (!Array.isArray(props.baseData.condiciones)) {
    props.baseData.condiciones = String(props.baseData.condiciones)
      .split(/\r?\n/)
      .map((entry) => normalizeConditionEntry(entry))
      .filter(Boolean)
    return
  }

  props.baseData.condiciones = props.baseData.condiciones
    .map((entry) => normalizeConditionEntry(entry))
    .filter(Boolean)
}

function startEditCondition(i) {
  if (!isQuoteEditable.value) return
  ensureConditionsArray()
  if (!canManageCondition(i)) return
  editIndex.value = i
  editText.value = props.baseData.condiciones[i]?.text || ''
}

function saveCondition(i) {
  if (!isQuoteEditable.value) return
  ensureConditionsArray()
  if (!canManageCondition(i)) return
  const v = String(editText.value || '').trim()
  if (!v) {
    props.baseData.condiciones.splice(i, 1)
  } else {
    props.baseData.condiciones.splice(i, 1, {
      ...props.baseData.condiciones[i],
      text: v
    })
  }
  emit('sync-form', {
    condiciones: props.baseData.condiciones
  })
  editIndex.value = -1
  editText.value = ''
}

function cancelEditCondition() {
  editIndex.value = -1
  editText.value = ''
}

function removeCondition(i) {
  if (!isQuoteEditable.value) return
  ensureConditionsArray()
  if (!canManageCondition(i)) return
  if (i >= 0 && i < props.baseData.condiciones.length) {
    props.baseData.condiciones.splice(i, 1)
    emit('sync-form', {
      condiciones: props.baseData.condiciones
    })
  }
}

function isServiceCondition(i) {
  return conditionsList.value?.[i]?.source === 'service'
}

function canManageCondition(i) {
  if (!isQuoteEditable.value || props.baseData?.lockConditionActions) return false
  return !isServiceCondition(i)
}


function conditionSourceLabel(condition) {
  if (condition?.source !== 'service') return 'Manual'
  return condition?.serviceName
    ? `Servicio: ${condition.serviceName}`
    : 'Servicio asociado'
}
const subtotal = computed(() =>
  roundAmount(
    items.value.reduce(
      (s, it) => s + roundAmount(it.qty * it.unitValue * (1 - it.discountPct / 100)),
      0
    )
  )
)

const ivaPct = ref(Number(props.baseData.ivaPorcentaje ?? props.baseData.porcentajeIva ?? 19))
const activeIvaId = ref(
  props.baseData.idIva != null && Number.isFinite(Number(props.baseData.idIva))
    ? Number(props.baseData.idIva)
    : null
)

function normalizeOptionalId(rawValue) {
  if (rawValue === null || rawValue === undefined || rawValue === '') return null
  const normalized = Number(rawValue)
  return Number.isFinite(normalized) && normalized > 0 ? normalized : null
}

onMounted(async () => {
  try {
    const res = await fetch(`${apiBaseUrl}/iva`)
    if (res.ok) {
      const list = await res.json()
      if (Array.isArray(list) && list.length) {
        const orderedIva = [...list].sort((a, b) => Number(b?.id_iva || 0) - Number(a?.id_iva || 0))
        const active = orderedIva.find((x) => x?.activo) || orderedIva[0]
        if (active) {
          if (active.porcentaje != null) ivaPct.value = Number(active.porcentaje)
          if (active.id_iva != null) activeIvaId.value = Number(active.id_iva)
        }
      }
    }
  } catch (e) {
    // ignore and keep default
  }
})

const iva = computed(() => Math.round(subtotal.value * (Number(ivaPct.value || 19) / 100)))
const total = computed(() => roundAmount(subtotal.value + iva.value))
const isReducedConnectionPlan = computed(() => {
  if (props.baseData.planType !== 'Período') return false
  const conexiones = Number(props.baseData.conexiones ?? 0)
  return conexiones === 1 || conexiones === 2
})

const periodMonthsForTotal = computed(() => {
  if (props.baseData.planType !== 'Período') return 1
  if (isReducedConnectionPlan.value) return 3
  return Math.max(1, Number(props.baseData.periodMonths ?? props.baseData.periods ?? 1))
})

const periodDiscountPct = computed(() => {
  if (props.baseData.planType !== 'Período') return 0
  const months = Math.max(1, Number(props.baseData.periodMonths ?? props.baseData.periods ?? 1))
  if (months >= 12) return 10
  if (months >= 6) return 5
  return 0
})

const periodBaseTotal = computed(() => {
  if (props.baseData.planType === 'Única') return total.value
  return roundAmount(total.value * periodMonthsForTotal.value)
})

const periodDiscountAmount = computed(() =>
  roundAmount(periodBaseTotal.value * (periodDiscountPct.value / 100))
)

const totalPeriod = computed(() => {
  if (props.baseData.planType === 'Única') return total.value
  return roundAmount(periodBaseTotal.value - periodDiscountAmount.value)
})

const periodDescriptor = computed(() => {
  if (props.baseData.planType === 'Única') {
    return 'Pago único'
  }

  const months = Math.max(1, Number(props.baseData.periodMonths ?? props.baseData.periods ?? 1))
  return `Cada ${months} mes${months === 1 ? '' : 'es'}`
})
const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const weasyPdfUrl = ref('')
const showWeasyPreview = ref(false)
const isQuoteConfirmed = computed(() => props.baseData.estado === 'CONFIRMADA')
const isQuoteEditable = computed(() => !isQuoteConfirmed.value)
const confirmActionLabel = computed(() => (isQuoteConfirmed.value ? 'Imprimir' : 'Confirmar cotización'))
const confirmActionIcon = computed(() => (isQuoteConfirmed.value ? '⎙' : '✓'))

function roundAmount(value) {
  return Math.round(Number(value) || 0)
}

function rowTotal(it) {
  return roundAmount(it.qty * it.unitValue * (1 - it.discountPct / 100))
}


function getEditedUnitValueInClp(it) {
  if (isDbItem(it)) return roundAmount(it.unitValue)
  const rawValue = Math.max(0, Number(editUnitValue.value || 0))
  if (editCurrency.value === 'UF') {
    return roundAmount(rawValue * Number(props.baseData.valorUf || 0))
  }
  return roundAmount(rawValue)
}


function getMonthsValidationError() {
  if (props.baseData.planType !== 'Período') return ''

  const conexiones = Number(props.baseData.conexiones ?? 0)
  const meses = Number(props.baseData.periodMonths ?? props.baseData.periods ?? 0)

  if (!Number.isFinite(meses) || meses <= 0) {
    return 'El período de contratación no puede ser cero ni negativo.'
  }

  if ((conexiones === 1 || conexiones === 2) && meses < 3) {
    return 'Para 1 o 2 conexiones, el período debe ser mayor o igual a 3 meses.'
  }

  return ''
}


function composeStoredConditions() {
  const conditionLines = (props.baseData.condiciones || [])
    .map((entry) => String(entry?.text || '').trim())
    .filter(Boolean)

  const observationLines = observationsList.value
    .map((entry) => String(entry || '').trim())
    .filter(Boolean)
    .map((entry) => `__OBS__ ${entry}`)

  const merged = [...conditionLines, ...observationLines]
  return merged.length ? merged.join('\n') : null
}

function validateRequiredClientData() {
  return true
}

const periodTotalLabel = computed(() => {
  if (props.baseData.planType !== 'Período') return `Total (${periodDescriptor.value})`
  const selectedMonths = Math.max(1, Number(props.baseData.periodMonths ?? props.baseData.periods ?? 1))
  const baseLabel = selectedMonths === 3 ? 'Total trimestral' : `Total (${periodDescriptor.value})`
  if (periodDiscountPct.value > 0) return `${baseLabel} con descuento`
  return baseLabel
})

function isDbItem(it) {
  return it?.source === 'db' || it?.autoPlan || it?.id_prestacion || it?.id_plan
}

function startEditItem(it) {
  if (!isQuoteEditable.value) return
  editItemId.value = it.id
  editQty.value = Number(it.qty || 1)
  editDiscount.value = Number(it.discountPct || 0)
  editUnitValue.value = Number((it.unitValueOriginal ?? it.unitValue) || 0)
  editCurrency.value = it.currency === 'UF' ? 'UF' : 'CLP'
}

function saveItemChanges(it) {
  if (!isQuoteEditable.value) return
  it.qty = Math.max(1, Number(editQty.value || 1))
  it.discountPct = Math.min(100, Math.max(0, Number(editDiscount.value || 0)))

  if (!isDbItem(it)) {
    const originalValue = Math.max(0, Number(editUnitValue.value || 0))
    const selectedCurrency = editCurrency.value === 'UF' ? 'UF' : 'CLP'
    it.currency = selectedCurrency
    it.unitValueOriginal = roundAmount(originalValue)
    it.unitValue = selectedCurrency === 'UF'
      ? roundAmount(originalValue * Number(props.baseData.valorUf || 0))
      : roundAmount(originalValue)
  }

  emit('sync-form', {
    items: props.baseData.items,
    condiciones: props.baseData.condiciones
  })

  cancelItemEdit()
}

function cancelItemEdit() {
  editItemId.value = null
  editQty.value = 1
  editDiscount.value = 0
  editUnitValue.value = 0
  editCurrency.value = 'CLP'
}

function splitConditionText(conditionText) {
  return String(conditionText || '')
    .split(/\r?\n/)
    .map((entry) => String(entry || '').trim())
    .filter(Boolean)
}

function getServiceConditionsFromItems() {
  const serviceConditions = []
  const seen = new Set()

  for (const item of props.baseData.items || []) {
    const itemId = item?.id ?? null
    if (itemId == null) continue

    const serviceName = String(item?.name || '').trim() || 'Servicio'
    const itemConditions = splitConditionText(item?.condiciones)

    for (const conditionText of itemConditions) {
      const dedupeKey = `${String(itemId)}::${conditionText}`
      if (seen.has(dedupeKey)) continue

      seen.add(dedupeKey)
      serviceConditions.push({
        text: conditionText,
        source: 'service',
        itemId,
        serviceName
      })
    }
  }

  return serviceConditions
}

function syncConditionsWithItems() {
  ensureConditionsArray()
  const manualConditions = props.baseData.condiciones.filter((condition) => condition.source !== 'service')
  props.baseData.condiciones = [...manualConditions, ...getServiceConditionsFromItems()]
}

function removeItem(id) {
  if (!isQuoteEditable.value) return
  const idx = props.baseData.items.findIndex((i) => String(i.id) === String(id))
  if (idx !== -1) {
    props.baseData.items.splice(idx, 1)
  }

  syncConditionsWithItems()
  emit('sync-form', {
    items: props.baseData.items,
    condiciones: props.baseData.condiciones
  })
}

async function replaceQuoteDetails(idCotizacion) {
  const detailResponse = await fetch(`${apiBaseUrl}/cotizacion_detalles`)
  if (!detailResponse.ok) {
    throw new Error('No se pudieron cargar los detalles para actualizar el borrador')
  }

  const allDetails = await detailResponse.json()
  const detailsToDelete = (Array.isArray(allDetails) ? allDetails : [])
    .filter((detail) => Number(detail.id_cotizacion) === Number(idCotizacion))

  for (const detail of detailsToDelete) {
    const deleteResponse = await fetch(`${apiBaseUrl}/cotizacion_detalles/${detail.id_detalle}`, {
      method: 'DELETE'
    })

    if (!deleteResponse.ok) {
      throw new Error('No se pudo limpiar el detalle anterior del borrador')
    }
  }

  for (const item of props.baseData.items || []) {
    const createResponse = await fetch(`${apiBaseUrl}/cotizacion_detalles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_cotizacion: idCotizacion,
        id_prestacion: item.id_prestacion ?? null,
        descripcion: item.name ?? null,
        cantidad: item.qty,
        valor_unitario: item.unitValue,
        descuento: item.discountPct ?? 0
      })
    })

    if (!createResponse.ok) {
      throw new Error(`No se pudo guardar el detalle ${item.name || ''}`.trim())
    }
  }
}

async function buildAndPersistQuote() {
  const payload = {
    tipo: props.baseData.planType === 'Única' ? 'UNICA' : 'PERIODO',
    id_cliente: normalizeOptionalId(props.baseData.idCliente),
    nombre_cliente: props.baseData.cliente ?? null,
    rut_cliente: props.baseData.rut ?? null,
    id_usuario: normalizeOptionalId(props.baseData.idUsuario),
    id_iva: normalizeOptionalId(activeIvaId.value),
    meses: props.baseData.planType === 'Única' ? null : props.baseData.periodMonths,
    conexiones: props.baseData.conexiones ?? 0,
    subtotal: subtotal.value,
    descuento_total: items.value.reduce((s, it) => s + it.qty * it.unitValue * (it.discountPct / 100), 0),
    iva_monto: iva.value,
    total: total.value,
    condiciones_adicionales: composeStoredConditions()
  }

  const headerResponse = await fetch(`${apiBaseUrl}/cotizaciones`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
      descripcion: item.name ?? null,
      cantidad: item.qty,
      valor_unitario: item.unitValue,
      descuento: item.discountPct ?? 0
    }

    const detailResponse = await fetch(`${apiBaseUrl}/cotizacion_detalles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(detailPayload)
    })

    if (!detailResponse.ok) {
      throw new Error(`No se pudo crear el detalle ${item.name || ''}`.trim())
    }
  }

  props.baseData.idCotizacion = idCotizacion
  props.baseData.estado = 'BORRADOR'
  emit('quote-saved', { idCotizacion, estado: 'BORRADOR' })
  emit('history-changed')
  return idCotizacion
}

async function updatePersistedDraft() {
  const idCotizacion = props.baseData.idCotizacion
  if (!idCotizacion) {
    throw new Error('No se encontró el borrador a actualizar')
  }

  const payload = {
    tipo: props.baseData.planType === 'Única' ? 'UNICA' : 'PERIODO',
    id_cliente: normalizeOptionalId(props.baseData.idCliente),
    nombre_cliente: props.baseData.cliente ?? null,
    rut_cliente: props.baseData.rut ?? null,
    id_usuario: normalizeOptionalId(props.baseData.idUsuario),
    id_iva: normalizeOptionalId(activeIvaId.value),
    meses: props.baseData.planType === 'Única' ? null : props.baseData.periodMonths,
    conexiones: props.baseData.conexiones ?? 0,
    subtotal: subtotal.value,
    descuento_total: items.value.reduce((s, it) => s + it.qty * it.unitValue * (it.discountPct / 100), 0),
    iva_monto: iva.value,
    total: total.value,
    condiciones_adicionales: composeStoredConditions()
  }

  const headerResponse = await fetch(`${apiBaseUrl}/cotizaciones/${idCotizacion}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)

  })

  if (!headerResponse.ok) {
    throw new Error('No se pudo actualizar el encabezado del borrador')
  }

  await replaceQuoteDetails(idCotizacion)

  props.baseData.estado = 'BORRADOR'
  emit('quote-saved', { idCotizacion, estado: 'BORRADOR' })
  emit('history-changed')
  return idCotizacion
}

async function saveDraft() {
  if (!isQuoteEditable.value) return
  const monthsError = getMonthsValidationError()
  if (monthsError) {
    errorMessage.value = monthsError
    alert(monthsError)
    return
  }

  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  resetWeasyPreview()

  try {
    if (props.baseData.idCotizacion) {
      await updatePersistedDraft()
      successMessage.value = 'Borrador actualizado correctamente.'
      return
    }

    await buildAndPersistQuote()
    successMessage.value = 'Borrador guardado en el historial.'
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Ocurrió un error inesperado al guardar el borrador'
  } finally {
    isSaving.value = false
  }
}


function resetWeasyPreview() {
  if (weasyPdfUrl.value) {
    URL.revokeObjectURL(weasyPdfUrl.value)
  }
  weasyPdfUrl.value = ''
  showWeasyPreview.value = false
}

function closeWeasyPreview() {
  showWeasyPreview.value = false
}

async function openWeasyPreview(idCotizacion) {
  const response = await fetch(`${apiBaseUrl}/cotizaciones/${idCotizacion}/weasy/pdf`)

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || 'No se pudo generar el PDF con WeasyPrint')
  }

  const pdfBlob = await response.blob()
  if (weasyPdfUrl.value) {
    URL.revokeObjectURL(weasyPdfUrl.value)
  }

  weasyPdfUrl.value = URL.createObjectURL(pdfBlob)
  showWeasyPreview.value = true
}

async function printQuote() {
  if (!validateRequiredClientData()) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    const monthsError = getMonthsValidationError()
    if (monthsError) {
      throw new Error(monthsError)
    }

    let idCotizacion = props.baseData.idCotizacion

    if (!isQuoteConfirmed.value) {
      idCotizacion = props.baseData.idCotizacion
        ? await updatePersistedDraft()
        : await buildAndPersistQuote()
    }

    if (!idCotizacion) {
      throw new Error('No se encontró una cotización confirmada para imprimir')
    }

    await openWeasyPreview(idCotizacion)
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Ocurrió un error al abrir la vista de impresión de la cotización'
  } finally {
    isSaving.value = false
  }
}

async function confirmQuote() {
  if (!validateRequiredClientData()) {
    return
  }

  const monthsError = getMonthsValidationError()
  if (monthsError) {
    errorMessage.value = monthsError
    alert(monthsError)
    return
  }

  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  resetWeasyPreview()

  try {
    const idCotizacion = props.baseData.idCotizacion
      ? await updatePersistedDraft()
      : await buildAndPersistQuote()

    const statusResponse = await fetch(`${apiBaseUrl}/cotizaciones/${idCotizacion}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ estado: 'CONFIRMADA' })
    })

    if (!statusResponse.ok) {
      throw new Error('No se pudo confirmar la cotización')
    }

    props.baseData.estado = 'CONFIRMADA'
    emit('quote-saved', { idCotizacion, estado: 'CONFIRMADA' })
    emit('history-changed')
    emit('quote-finalized', { idCotizacion })
    successMessage.value = 'Cotización confirmada correctamente.'
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Ocurrió un error inesperado al confirmar la cotización'
  } finally {
    isSaving.value = false
  }
}

async function discardQuote() {
  if (!isQuoteEditable.value) return
  const shouldDiscard = window.confirm('¿Estás seguro de que deseas descartar esta cotización?')
  if (!shouldDiscard) return

  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  resetWeasyPreview()

  try {
    if (props.baseData.idCotizacion && props.baseData.estado !== 'CONFIRMADA') {
      const response = await fetch(`${apiBaseUrl}/cotizaciones/${props.baseData.idCotizacion}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error('No se pudo descartar la cotización guardada en borrador')
      }
      emit('history-changed')
    }

    emit('discard')
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Ocurrió un error inesperado al descartar la cotización'
  } finally {
    isSaving.value = false
  }
}

function backToHistory() {
  resetWeasyPreview()
  emit('back')
}
</script>


<template>
<section class="preview">

  <header class="preview-header">
    <div class="doc-mark">Documento de cotización</div>
    <h4 class="tipo">Cotización tipo {{ baseData.planType }}</h4>
    <h4 class="client">{{ baseData.cliente || '—' }}</h4>
    <small class="client">RUT: {{ baseData.rut || '—' }}</small>
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

  <!-- ITEMS -->
  <tr v-for="it in items" :key="it.id">
    <template v-if="editItemId === it.id">
      <td>
        <input v-model.number="editQty" type="number" min="1" class="edit-input" />
      </td>
      <td>{{ it.name }}</td>
      <td>
        <template v-if="isDbItem(it)">${{ roundAmount(it.unitValue) }}</template>
        <input
          v-else
          v-model.number="editUnitValue"
          type="number"
          min="0"
          class="edit-input"
        />
      </td>
      <td>
        <input v-model.number="editDiscount" type="number" min="0" max="100" class="edit-input" />%
      </td>
      <td class="bold">${{ roundAmount(editQty * getEditedUnitValueInClp(it) * (1 - editDiscount / 100)) }}</td>
      <td class="actions">
        <button @click="saveItemChanges(it)">💾</button>
        <button @click="cancelItemEdit">✖️</button>
      </td>
    </template>
    <template v-else>
      <td>{{ it.qty }}</td>
      <td>{{ it.name }}</td>
      <td>${{ roundAmount(it.unitValue) }}</td>
      <td>{{ it.discountPct }}%</td>
      <td class="bold">${{ rowTotal(it).toFixed(0) }}</td>
      <td class="actions">
        <template v-if="isQuoteEditable">
          <button @click="startEditItem(it)">✏️</button>
          <button @click="removeItem(it.id)">🗑️</button>
        </template>
      </td>
    </template>
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
      <span>Subtotal mensual</span>
      <strong>${{ subtotal.toFixed(0) }}</strong>
    </div>
    <div>
      <span>IVA mensual ({{ Number(ivaPct) % 1 === 0 ? Number(ivaPct).toFixed(0) : Number(ivaPct).toFixed(1) }}%)</span>
      <strong>${{ iva.toFixed(0) }}</strong>
    </div>
    <div>
      <span>Total mensual</span>
      <strong>${{ total.toFixed(0) }}</strong>
    </div>
    <div v-if="periodDiscountPct > 0">
      <span>Descuento período ({{ periodDiscountPct }}% sobre total del período)</span>
      <strong>-${{ periodDiscountAmount.toFixed(0) }}</strong>
    </div>
    <div class="grand-total">
      <span>{{ periodTotalLabel }}</span>
      <strong>${{ totalPeriod.toFixed(0) }}</strong>
    </div>
  </div>

  <footer class="preview-footer">
    Documento generado por: <strong>{{ baseData.ejecutivo || 'Usuario' }}</strong>
  </footer>

</section>
  
  <!-- CONDICIONES ADICIONALES -->
  <div class="conditions" v-if="conditionsList.length">
    <h5 class="conditions-title">Condiciones adicionales</h5>
    <ul class="conditions-list">
      <li v-for="(c, i) in conditionsList" :key="i" class="conditions-item">
        <template v-if="editIndex === i">
          <input class="condition-input" v-model="editText" />
          <button class="cond-action" @click="saveCondition(i)">Guardar</button>
          <button class="cond-action" @click="cancelEditCondition">Cancelar</button>
        </template>
        <template v-else>
          <span
            class="cond-service"
            :class="{ 'cond-service-linked': c.source === 'service', 'cond-service-manual': c.source !== 'service' }"
          >
            {{ conditionSourceLabel(c) }}
          </span>
          <span
            class="cond-text"
            :class="{ 'cond-text-linked': c.source === 'service', 'cond-text-manual': c.source !== 'service' }"
          >
            {{ c.text }}
          </span>
          <span class="conditions-item-actions">
            <button
              v-if="canManageCondition(i)"
              @click="startEditCondition(i)"
              title="Editar"
            >✏️</button>
            <button
              v-if="canManageCondition(i)"
              @click="removeCondition(i)"
              title="Eliminar"
            >🗑️</button>
          </span>
        </template>
      </li>
    </ul>
  
</div>


<div class="conditions" v-if="observationsList.length">
  <h5 class="conditions-title">Observaciones</h5>
  <ul class="conditions-list">
    <li v-for="(o, i) in observationsList" :key="`obs-${i}`" class="conditions-item">
      <span class="cond-service cond-service-manual">Observación</span>
      <span class="cond-text cond-text-manual">{{ o }}</span>
      <span></span>
    </li>
  </ul>
</div>

<div v-if="showWeasyPreview && weasyPdfUrl" class="weasy-preview-overlay" @click.self="closeWeasyPreview">
  <div class="weasy-preview-modal">
    <div class="weasy-preview-header">
      <h5>Vista previa PDF (WeasyPrint)</h5>
      <div class="weasy-preview-actions">
        <button class="btn-close" @click="closeWeasyPreview">Cerrar</button>
      </div>
    </div>
    <iframe
      :src="weasyPdfUrl"
      class="weasy-preview-frame"
      title="Vista previa cotización WeasyPrint"
    />
  </div>
</div>

<div class="final-actions">
  <button
    v-if="isQuoteEditable"
    class="final-btn btn-discard"
    :disabled="isSaving"
    @click="discardQuote"
  >
    <span class="btn-icon" aria-hidden="true">✕</span>
    <span>{{ isSaving ? 'Procesando...' : 'Descartar' }}</span>
  </button>

  <button
    v-if="isQuoteEditable"
    class="final-btn btn-draft"
    :disabled="isSaving"
    @click="saveDraft"
  >
    <span class="btn-icon" aria-hidden="true">✎</span>
    <span>{{ isSaving ? 'Guardando...' : 'Guardar borrador' }}</span>
  </button>

  <button
    class="final-btn btn-confirm"
    :disabled="isSaving"
    @click="isQuoteConfirmed ? printQuote() : confirmQuote()"
  >
    <span class="btn-icon" aria-hidden="true">{{ isSaving ? '…' : confirmActionIcon }}</span>
    <span>{{ isSaving ? 'Guardando...' : confirmActionLabel }}</span>
  </button>
</div>
<p v-if="errorMessage" class="status-message error">{{ errorMessage }}</p>
<p v-if="successMessage" class="status-message success">{{ successMessage }}</p>
</template>

<style scoped>
.preview {
  margin: 0 auto;
  width: min(760px, 100%);
  background: #fff;
  border: 1px solid #d6dde7;
  box-shadow: 0 10px 25px rgba(15, 21, 64, 0.08);
  border-radius: 4px;
  padding: 24px 24px 18px;
}

.preview-header {
  border-bottom: 1px solid #dbe2ec;
  padding-bottom: 12px;
}

.doc-mark {
  font-size: 11px;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.08em;
  margin-bottom: 4px;
}

/* === TABLA GENERAL === */
.services-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: white;
  margin-top: 14px;
  overflow: hidden;
  color: black;
}

.services-table th {
  font-weight: 600;
  background: #edf2f7;
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

 .edit-input {
  width: 80px;
  padding: 4px 6px;
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
  border: 1px solid #d9e1eb;
  border-radius: 4px;
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
/* === CONDICIONES ADICIONALES === */
.conditions {
  margin-top: 14px;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #d9e1eb;
  border-radius: 4px;
}
.conditions-title {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #0f172a;
  font-weight: 600;
}
.conditions-list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 13px;
}
.conditions-list li {
  margin-bottom: 6px;
}
.conditions-item {
  display: grid;
  grid-template-columns: 1fr 1.7fr 0.8fr;
  align-items: center;
  gap: 10px;
}

.cond-service {
  display: inline-flex;
  align-items: center;
  min-width: 150px;
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}

.cond-service-linked {
  color: #1e40af;
}

.cond-service-manual {
  color: #166534;
}
.conditions-item .cond-text {
  flex: 1 1 auto;
  border-radius: 9px;
  font-size: 11px;
  text-align: center;
}

.cond-text-linked {
  background: rgba(37, 99, 235, 0.14);
  color: #1e40af;
}

.cond-text-manual {
  background: rgba(22, 163, 74, 0.14);
  color: #166534;
}
.conditions-item .conditions-item-actions button {
  background: none;
  border: none;
  cursor: pointer;
  margin-left: 6px;
  opacity: 0.7;
}
.condition-input {
  flex: 1 1 auto;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid rgba(15,23,42,0.08);
  margin-right: 8px;
}
.cond-action {
  padding: 6px 8px;
  border-radius: 6px;
  border: none;
  background: #eef2ff;
  color: #0f172a;
  font-weight: 600;
  cursor: pointer;
  margin-left: 6px;
}
.tipo {
  font-size: 12px;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 6px;
}
.client{
    color: #0f172a;
    font-weight: 600;
    margin: 0;
}

.preview-footer {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid #dbe2ec;
  color: #475569;
  font-size: 12px;
}

.weasy-preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 999;
}

.weasy-preview-modal {
  width: min(980px, 100%);
  max-height: calc(100vh - 40px);
  border: 1px solid #d9e1eb;
  border-radius: 10px;
  padding: 12px;
  background: #f8fafc;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.35);
}

.weasy-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.weasy-preview-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weasy-preview-header h5 {
  margin: 0;
  color: #0f172a;
}

.weasy-preview-frame {
  width: 100%;
  height: min(74vh, 700px);
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
}

.btn-download {
  background: #0f766e;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
}

.btn-download:hover {
  background: #115e59;
}

.btn-close {
  background: #475569;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
}

.btn-close:hover {
  background: #334155;
}

.btn-back-inline {
  background: #0f766e;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
}

.btn-back-inline:hover {
  background: #115e59;
}

/* === BOTONES FINALES === */
.final-actions {
  margin-top: 24px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 14px;
}

.final-btn {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #1e293b;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
}

.final-btn:hover:not(:disabled) {
  background: #f8fafc;
}

.final-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 14px;
  line-height: 1;
  font-weight: 700;
}

.btn-back {
  border-color: #93c5fd;
  color: #1d4ed8;
}

.btn-back:hover:not(:disabled) {
  border-color: #60a5fa;
  background: #eff6ff;
}

/* DESCARTAR */
.btn-discard {
  border-color: #d1d5db;
  color: #475569;
}

.btn-discard:hover:not(:disabled) {
  border-color: #94a3b8;
  color: #334155;
}

/* BORRADOR */
.btn-draft {
  border-color: #93c5fd;
  color: #1d4ed8;
}

.btn-draft:hover:not(:disabled) {
  border-color: #60a5fa;
  background: #eff6ff;
}

/* CONFIRMAR / IMPRIMIR */
.btn-confirm {
  border-color: #67e8f9;
  color: #0f766e;
}

.btn-confirm:hover:not(:disabled) {
  border-color: #22d3ee;
  background: #ecfeff;
}


@media (max-width: 780px) {
  .preview { padding: 14px; }
  .services-table th, .services-table td { padding: 8px; font-size: 12px; }
  .final-actions { justify-content: stretch; }
}
</style>
