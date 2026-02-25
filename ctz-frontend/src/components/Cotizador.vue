<script setup>
import { reactive, computed, watch, ref, onMounted } from 'vue'
import axios from 'axios'; // O usar fetch nativo

const emit = defineEmits(['back', 'update-preview', 'add-service'])

const props = defineProps({
  tabId: {
    type: [String, Number],
    required: true
  },
  initialData: {
    type: Object,
    default: null
  }
})

const valorUf = ref(null);
const ivaPct = ref(19)
const loading = ref(true);
const obtenerUf = async () => {
  try {
    const response = await axios.get('https://mindicador.cl/api/uf');
    // El valor actual es el primero en la serie 'serie'
    valorUf.value = response.data.serie[0].valor;
  } catch (error) {
    console.error('Error al obtener la UF:', error);
  } finally {
    loading.value = false;
  }
};
const STORAGE_KEY = computed(() => `cotizador_form_${props.tabId}`)

function getStoredUser() {
  try {
    const raw = localStorage.getItem('cotizador_user')
    return raw ? JSON.parse(raw) : null
  } catch (error) {
    return null
  }
}

const storedUser = getStoredUser()
const defaultForm = {
  idUsuario: storedUser?.id_usuario ?? null,
  ejecutivo: storedUser?.nombre || storedUser?.email || '',
  cliente: '',
  rut: '',
  planType: 'Período',
  periodMonths: 3,
  conexiones: 1,
  condicion:'',
  condiciones: [],
  observacion: '',
  observaciones: [],
  cantidad: 1,
  moneda: 'CLP',
  valor: 0,
  valor_original: 0,
  descuento: 0,
  seleccionado: '',
  manualServiceName: '',
  manualServiceCurrency: 'CLP',
  items: []
}

const MANUAL_SERVICE_OPTION = '__manual_service__'

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

function ensureConditionsArray() {
  if (!Array.isArray(form.condiciones)) {
    form.condiciones = String(form.condiciones || '')
      .split(/\r?\n/)
      .map((entry) => normalizeConditionEntry(entry))
      .filter(Boolean)
    return
  }

  form.condiciones = form.condiciones
    .map((entry) => normalizeConditionEntry(entry))
    .filter(Boolean)
}

function splitConditionText(conditionText) {
  return String(conditionText || '')
    .split(/\r?\n/)
    .map((entry) => String(entry || '').trim())
    .filter(Boolean)
}

function isQuoteOnRequestCondition(text) {
  return /valor\s+a\s+cotizar/i.test(String(text || ''))
}

function sanitizeServiceConditions(conditionText) {
  return splitConditionText(conditionText)
    .filter((text) => !isQuoteOnRequestCondition(text))
    .join('\n')
}

function getServiceConditionsFromItems() {
  const serviceConditions = []
  const seen = new Set()

  for (const item of form.items) {
    const itemId = item?.id ?? null
    if (itemId == null) continue

    const serviceName = String(item?.name || '').trim() || 'Servicio'
    const itemConditions = splitConditionText(item?.condiciones)

    for (const text of itemConditions) {
      const dedupeKey = `${String(itemId)}::${text}`
      if (seen.has(dedupeKey)) continue

      seen.add(dedupeKey)
      serviceConditions.push({
        text,
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
  const manualConditions = form.condiciones.filter((entry) => entry.source !== 'service')
  form.condiciones = [...manualConditions, ...getServiceConditionsFromItems()]
}

function hydrateItemConditionsFromPrestaciones() {
  if (!Array.isArray(form.items) || !prestaciones.value.length) return

  const conditionsByPrestacionId = new Map(
    prestaciones.value.map((prestacion) => [
      Number(prestacion.id_prestacion),
      sanitizeServiceConditions(prestacion.condiciones)
    ])
  )

  let updated = false
  for (const item of form.items) {
    if (!item || item.condiciones || item.id_prestacion == null) continue

    const serviceConditions = conditionsByPrestacionId.get(Number(item.id_prestacion))
    if (!serviceConditions) continue

    item.condiciones = sanitizeServiceConditions(serviceConditions)
    updated = true
  }

  if (updated) {
    syncConditionsWithItems()
  }
}

function normalizeInitialData(data) {
  if (!data) return {}
  return {
    ...data,
    idUsuario: data.idUsuario ?? data.id_usuario ?? null,
    ejecutivo: data.ejecutivo ?? data.user ?? '',
    cliente: data.cliente ?? data.name ?? '',
    conexiones: data.conexiones ?? data.connections ?? 1,
    condiciones: data.condiciones ?? data.conditions ?? '',
    observaciones: data.observaciones ?? data.observations ?? '',
    items: Array.isArray(data.items)
      ? JSON.parse(JSON.stringify(data.items))
      : []
  }
}

function ensureObservationsArray() {
  if (!Array.isArray(form.observaciones)) {
    form.observaciones = String(form.observaciones || '')
      .split(/\r?\n/)
      .map((entry) => String(entry || '').trim())
      .filter(Boolean)
    return
  }

  form.observaciones = form.observaciones
    .map((entry) => String(entry || '').trim())
    .filter(Boolean)
}

const savedForm = localStorage.getItem(STORAGE_KEY.value)
const initialForm = {
  ...structuredClone(defaultForm),
  ...normalizeInitialData(props.initialData),
  ...(savedForm ? JSON.parse(savedForm) : {})
}
console.log('Initial form data:', initialForm)

const form = reactive(initialForm)

function syncFromPreview(payload = {}) {
  if (Object.prototype.hasOwnProperty.call(payload, 'items') && Array.isArray(payload.items)) {
    form.items = JSON.parse(JSON.stringify(payload.items))
  }

  if (Object.prototype.hasOwnProperty.call(payload, 'condiciones')) {
    const incomingConditions = Array.isArray(payload.condiciones)
      ? payload.condiciones
      : String(payload.condiciones || '')
        .split(/\r?\n/)

    form.condiciones = incomingConditions
      .map((entry) => normalizeConditionEntry(entry))
      .filter(Boolean)
  }

  if (Object.prototype.hasOwnProperty.call(payload, 'observaciones')) {
    const incomingObservations = Array.isArray(payload.observaciones)
      ? payload.observaciones
      : String(payload.observaciones || '').split(/\r?\n/)

    form.observaciones = incomingObservations
      .map((entry) => String(entry || '').trim())
      .filter(Boolean)
  }

  syncConditionsWithItems()
}

defineExpose({
  syncFromPreview
})


const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const prestaciones = ref([])
const prestacionesLoading = ref(false)
const prestacionesError = ref('')
const serviceSelectionNotice = ref('')
const planes = ref([])
const planesLoading = ref(false)
const planesError = ref('')

function roundAmount(value) {
  return Math.round(Number(value) || 0)
}

function getDisplayedCurrency() {
  if (form.planType === 'Única' && form.seleccionado === MANUAL_SERVICE_OPTION) {
    return form.manualServiceCurrency
  }
  return form.moneda
}

function getValueInClp() {
  const value = Number(form.valor || 0)
  if (form.planType === 'Única' && form.seleccionado === MANUAL_SERVICE_OPTION && form.manualServiceCurrency === 'UF') {
    return roundAmount(value * Number(valorUf.value || 0))
  }
  return roundAmount(value)
}

function formatRut(e) {
  let v = e.target.value

  // Solo números y K
  v = v.replace(/[^0-9kK]/g, '').toUpperCase()

  if (v.length <= 1) {
    e.target.value = v
    form.rut = v
    return
  }

  const body = v.slice(0, -1)
  const dv = v.slice(-1)

  // Puntos
  let formatted = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.')

  const result = `${formatted}-${dv}`

  e.target.value = result
  form.rut = result
}
function addService() {
  if (!form.seleccionado) return

  if (form.planType === 'Única' && form.seleccionado === MANUAL_SERVICE_OPTION) {
    const manualName = String(form.manualServiceName || '').trim()
    if (!manualName) return

    const selectedCurrency = form.manualServiceCurrency === 'UF' ? 'UF' : 'CLP'
    const baseValue = Math.max(0, Number(form.valor || 0))
    const convertedValue = selectedCurrency === 'UF'
      ? roundAmount(baseValue * Number(valorUf.value || 0))
      : roundAmount(baseValue)

    const manualItemId = Date.now()
    
    form.items.push({
      id: manualItemId,
      name: manualName,
      qty: form.cantidad,
      unitValue: convertedValue,
      unitValueOriginal: roundAmount(baseValue),
      currency: selectedCurrency,
      discountPct: form.descuento,
      condiciones: null,
      source: 'manual'
    })

    form.seleccionado = ''
    form.manualServiceName = ''
    form.manualServiceCurrency = 'CLP'
    form.cantidad = 1
    form.valor = 0
    form.descuento = 0
    return
  }

  const prestacionSeleccionada = prestaciones.value.find(
    (it) => it.id_prestacion === Number(form.seleccionado)
  )

  if (!prestacionSeleccionada) return

  const itemId = Date.now()
  form.items.push({
    id: itemId,
    id_prestacion: prestacionSeleccionada.id_prestacion,
    name: prestacionSeleccionada.nombre,
    qty: form.cantidad,
    unitValue: roundAmount(form.valor),
    discountPct: form.descuento,
    condiciones: sanitizeServiceConditions(prestacionSeleccionada.condiciones),
    source: 'db'
  })

  syncConditionsWithItems()

  // Limpiar inputs
  form.seleccionado = ''
  form.manualServiceName = ''
  form.manualServiceCurrency = 'CLP'
  form.cantidad = 1
  form.valor = 0
  form.descuento = 0

}
function addCondicion() {
  ensureConditionsArray()
  const condicion = String(form.condicion || '').trim()
  if (!condicion) return
  form.condiciones.push({
    text: condicion,
    source: 'manual',
    itemId: null,
    serviceName: null
  })
  form.condicion = ''

}

function addObservacion() {
  ensureObservationsArray()
  const observacion = String(form.observacion || '').trim()
  if (!observacion) return
  form.observaciones.push(observacion)
  form.observacion = ''
}

async function cargarPrestaciones() {
  prestacionesLoading.value = true
  prestacionesError.value = ''
  try {
    const response = await fetch(`${apiBaseUrl}/prestaciones`)
    if (!response.ok) {
      throw new Error('No fue posible cargar las prestaciones')
    }

    const data = await response.json()
    prestaciones.value = (Array.isArray(data) ? data : []).filter((it) => it.activo)
    hydrateItemConditionsFromPrestaciones()
  } catch (error) {
    prestacionesError.value = error instanceof Error
      ? error.message
      : 'Error inesperado al cargar prestaciones'
  } finally {
    prestacionesLoading.value = false
  }
}

async function cargarPlanes() {
  planesLoading.value = true
  planesError.value = ''
  try {
    const response = await fetch(`${apiBaseUrl}/planes`)
    if (!response.ok) {
      throw new Error('No fue posible cargar los planes')
    }

    const data = await response.json()
    planes.value = (Array.isArray(data) ? data : [])
      .filter((it) => it.activo)
      .sort((a, b) => Number(a.conexiones_incluidas || 0) - Number(b.conexiones_incluidas || 0))
  } catch (error) {
    planesError.value = error instanceof Error
      ? error.message
      : 'Error inesperado al cargar planes'
  } finally {
    planesLoading.value = false
  }
}

function syncPlanItems() {
  const manualItems = form.items.filter((it) => !it.autoPlan)

  const normalizedPlanNames = planes.value
    .map((plan) => String(plan?.nombre || '').trim().toLowerCase())
    .filter(Boolean)

  const isManualPlanItem = (item) => {
    if (!item || item.autoPlan || item.id_plan != null) return true
    const itemName = String(item.name || '').trim().toLowerCase()
    if (!itemName) return false
    return normalizedPlanNames.some((planName) => itemName.includes(planName))
  }

  const nonPlanManualItems = form.planType === 'Período'
    ? manualItems.filter((item) => !isManualPlanItem(item))
    : manualItems

  if (form.planType === 'Única' || !planes.value.length) {
    form.items = nonPlanManualItems
    syncConditionsWithItems()
    return
  }

  const conexionesSolicitadas = Math.max(0, Number(form.conexiones || 0))
  const planBase = [...planes.value]
    .reverse()
    .find((it) => Number(it.conexiones_incluidas || 0) <= conexionesSolicitadas)
    ?? planes.value[0]
  if (!planBase) {
    form.items = nonPlanManualItems
    syncConditionsWithItems()
    return
  }

  const conexionesIncluidas = Number(planBase.conexiones_incluidas || 0)
  const conexionesExtra = Math.max(0, conexionesSolicitadas - conexionesIncluidas)

  const planItems = [{
    id: `auto-plan-${planBase.id_plan}`,
    id_plan: planBase.id_plan,
    name: `${planBase.nombre} (${conexionesIncluidas} conexiones)`,
    qty: 1,
    unitValue: roundAmount(planBase.valor_plan_mensual),
    discountPct: 0,
    condiciones: planBase.condiciones || null,
    autoPlan: true,
    source: 'db'
  }]

  if (conexionesExtra > 0) {
    planItems.push({
      id: `auto-plan-extra-${planBase.id_plan}`,
      name: `Conexiones adicionales (${planBase.nombre})`,
      qty: conexionesExtra,
      unitValue: roundAmount(planBase.valor_conexion_adicional),
      discountPct: 0,
      autoPlan: true,
      source: 'db'
    })
  }

  form.items = [...planItems, ...nonPlanManualItems]
  syncConditionsWithItems()
}

function onSelectPrestacion() {
  serviceSelectionNotice.value = ''

  if (form.seleccionado === MANUAL_SERVICE_OPTION) {
    form.manualServiceCurrency = 'CLP'
    form.moneda = form.manualServiceCurrency
    form.valor = 0
    form.valor_original = 0
    return
  }

  const prestacionSeleccionada = prestaciones.value.find(
    (it) => it.id_prestacion === Number(form.seleccionado)
  )

  if (!prestacionSeleccionada) return

  if (isQuoteOnRequestCondition(prestacionSeleccionada.condiciones)) {
    serviceSelectionNotice.value = 'Este servicio se cotiza bajo evaluación comercial (valor a cotizar). El aviso no se incluirá en el PDF.'
  }

  // guardamos el valor real de BD
  form.valor_original = Number(prestacionSeleccionada.valor_unitario || 0)

  let valor = form.valor_original

  if (prestacionSeleccionada.clp) {
    form.moneda = 'CLP'
  } else {
    form.moneda = 'UF'
    valor = roundAmount(form.valor_original * valorUf.value)
  }

  // lo que verá el usuario
  form.valor = roundAmount(valor)
}


async function loadIva() {
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/iva`)
    if (res.ok) {
      const list = await res.json()
      if (Array.isArray(list) && list.length) {
        const orderedIva = [...list].sort((a, b) => Number(b?.id_iva || 0) - Number(a?.id_iva || 0))
        const active = orderedIva.find((x) => x?.activo) || orderedIva[0]
        if (active && active.porcentaje != null) ivaPct.value = Number(active.porcentaje)
      }
    }
  } catch (e) {
    // ignore
  }
}

onMounted(() => {
  ensureConditionsArray()
  ensureObservationsArray()
  syncConditionsWithItems()
  cargarPrestaciones()
  cargarPlanes()
  obtenerUf()
  loadIva()
})

watch(
  () => form.items,
  () => {
    syncConditionsWithItems()
  },
  { deep: true }
)

const subtotal = computed(() =>
  roundAmount(
    form.items.reduce((sum, it) => {
      const lineTotal = roundAmount(it.qty * it.unitValue * (1 - it.discountPct / 100))
      return sum + lineTotal
    }, 0)
  )
)

const iva = computed(() => Math.round(subtotal.value * (Number(ivaPct.value || 19) / 100)))
const total = computed(() => roundAmount(subtotal.value + iva.value))
const minPeriodMonths = computed(() => {
  if (form.planType !== 'Período') return 1
  const conexiones = Number(form.conexiones || 0)
  return conexiones === 1 || conexiones === 2 ? 3 : 1
})

const isManualServiceMode = computed(() => (
  form.planType === 'Única' && form.seleccionado === MANUAL_SERVICE_OPTION
))

function validateRut(value) {
  const cleaned = String(value || '').replace(/\./g, '').replace(/-/g, '').toUpperCase()
  if (!cleaned) return true
  if (!/^\d{7,8}[\dK]$/.test(cleaned)) return false

  const body = cleaned.slice(0, -1)
  const dv = cleaned.slice(-1)

  let sum = 0
  let factor = 2
  for (let index = body.length - 1; index >= 0; index -= 1) {
    sum += Number(body[index]) * factor
    factor = factor === 7 ? 2 : factor + 1
  }

  const remainder = 11 - (sum % 11)
  let expectedDv = ''
  if (remainder === 11) expectedDv = '0'
  else if (remainder === 10) expectedDv = 'K'
  else expectedDv = String(remainder)

  return dv === expectedDv
}

const rutError = computed(() => !validateRut(form.rut))

function buildPreview() {
  return {
    idUsuario: form.idUsuario ?? null,
    ejecutivo: form.ejecutivo,
    cliente: form.cliente,
    rut: form.rut,

    planType: form.planType,
    periodMonths: form.periodMonths,
    conexiones: form.conexiones,
    observaciones: form.observaciones,
    condiciones: form.condiciones,
    moneda: form.moneda,
    valorUf: Number(valorUf.value || 0),
    items: form.items,
  }
}

watch(form, () => {
  emit('update-preview', buildPreview())
}, { deep: true, immediate: true })

watch(
  () => form.planType,
  () => {
    if (form.planType === 'Única') {
      syncPlanItems()
    }
  },
  { immediate: true }
)

watch(
  [() => form.conexiones, () => form.planType],
  () => {
    if (form.planType !== 'Período') return
    if (Number(form.periodMonths || 0) < minPeriodMonths.value) {
      form.periodMonths = minPeriodMonths.value
    }
  },
  { immediate: true }
)
watch(
  form,
  (v) => {
    localStorage.setItem(
      STORAGE_KEY.value,
      JSON.stringify(v)
    )
  },
  { deep: true }
)

</script>


<template>
  <section class="cotizador-card" :class="{ 'manual-service-active': isManualServiceMode }">
    <div class="card-header">
      <div>
        <h3>Datos de la Cotización</h3>
        <div class="muted">Ejecutivo/a: {{ form.ejecutivo }}</div>
      </div>
      <div class="mode-pill">
        <button
          class="pill"
          :class="{ active: form.planType === 'Período' }"
          @click="form.planType = 'Período'"
          type="button"
        >
          Período
        </button>
        <button
          class="pill"
          :class="{ active: form.planType === 'Única' }"
          @click="form.planType = 'Única'"
          type="button"
        >
          Única
        </button>
      </div>
    </div>
    <div class="card-body">
      <div class="section">
        <div class="section-head">
          <h4>Datos del cliente</h4>
        </div>
        <div class="row two">
          <div class="field">
            <label>RUT Persona/Empresa</label>
            <input
              v-model="form.rut"
              placeholder="Ej: 12.345.678-5"
              @input="formatRut"
              maxlength="12"
            />
            <small v-if="rutError" class="error">RUT inválido</small>
          </div>
          <div class="field">
            <label>Nombre/Razón Social</label>
            <input v-model="form.cliente" placeholder="Ej: Empresa ABC Ltda." />
          </div>
        </div>
      </div>

      <div class="config-row" v-if="form.planType === 'Período'">
        <div class="section quote-period-section">
          <div class="section-head">
            <h4>Período de cotización</h4>
          </div>
          <div class="field compact-field">
            <label>Cantidad de meses</label>
            <input type="number" :min="minPeriodMonths" v-model.number="form.periodMonths" />
          </div>
        </div>

        <div class="section config-plan-section">
          <div class="section-head">
            <h4>Configuración del plan</h4>
            <button
              class="btn-add circle"
              type="button"
              @click="syncPlanItems"
              aria-label="Agregar conexión"
              title="Agregar conexión"
            >
              <img src="/icon_add.png" alt="Agregar" class="icon-add">
            </button>
          </div>
          <div class="row two">
            <div class="field">
              <label>Cantidad de Conexiones</label>
              <input type="number" min="0" v-model.number="form.conexiones" />
              <small v-if="planesLoading">Cargando planes...</small>
              <small v-else-if="planesError" class="error">{{ planesError }}</small>
            </div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-head">
          <h4>Servicios</h4>
         <button class="btn-add circle" @click="addService">
            <img src="/icon_add.png" alt="Agregar" class="icon-add">
         </button>
        </div>

        <div class="items-list">
          <div class="item" :class="{ 'manual-service-active': isManualServiceMode }">
            <div class="svc-main">
                <select v-model="form.seleccionado" class="svc-name" @change="onSelectPrestacion">
                  <option disabled value="">Selecciona un servicio</option>
                  <option v-if="form.planType === 'Única'" :value="MANUAL_SERVICE_OPTION">Crear servicio</option>
                    <option
                        v-for="prestacion in prestaciones"
                        :key="prestacion.id_prestacion"
                         :value="prestacion.id_prestacion"
                      >
                        {{ prestacion.nombre }}
                  </option>
                </select>
                <input
                  v-if="form.planType === 'Única' && form.seleccionado === MANUAL_SERVICE_OPTION"
                  v-model="form.manualServiceName"
                  class="manual-service-input"
                  type="text"
                  placeholder="Nombre del servicio manual"
                />
                <small v-if="prestacionesLoading">Cargando prestaciones...</small>
                <small v-else-if="prestacionesError" class="error">{{ prestacionesError }}</small>
            </div>
            <div class="svc-controls">
              <div class="mini-field">
                <label>Cantidad</label>
                <input type="number" min="0" class="small" v-model.number="form.cantidad" />
              </div>
              <div class="mini-field">
                <label>Valor ({{ getDisplayedCurrency() }})</label>
                <input v-if="form.planType === 'Período'" type="number" min="0" class="medium" v-model.number="form.valor_original" />
                <input v-else type="number" min="0" class="medium" v-model.number="form.valor" />
              </div>
              <div class="mini-field" v-if="form.planType === 'Única' && form.seleccionado === MANUAL_SERVICE_OPTION">
                <label>Moneda</label>
                <select class="small" v-model="form.manualServiceCurrency">
                  <option value="CLP">CLP</option>
                  <option value="UF">UF</option>
                </select>
              </div>
              <div class="mini-field">
                <label>Descuento</label>
                <div class="discount-input">
                  <input type="number" min="0" max="100" class="tiny" v-model.number="form.descuento" />
                  <span>%</span>
                </div>
              </div>
            </div>
            <div v-if="getDisplayedCurrency() === 'UF'" class="uf-info-box">
              <div class="uf-loading" v-if="loading">
                <span class="spinner">⟳</span> Cargando valor UF...
              </div>
              <template v-else>
                <div class="uf-item">
                  <span class="uf-label">Valor UF</span>
                  <span class="uf-value">${{ valorUf.toLocaleString('es-CL') }}</span>
                </div>
                <div class="uf-item" v-if="valorUf && form.valor > 0">
                  <span class="uf-label">En CLP</span>
                  <span class="uf-converted">${{ getValueInClp().toLocaleString('es-CL') }}</span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-head">
          <h4>Condiciones adicionales</h4>
          <button class="btn-add circle" type="button" @click="addCondicion">
            <img src="/icon_add.png" alt="Agregar" class="icon-add">
          </button>
        </div>
        <div class="field">
          <input v-model="form.condicion" placeholder="Ej: capacitación: costo $0" @keyup.enter="addCondicion" />
        </div>
        <small v-if="serviceSelectionNotice" class="selection-notice">{{ serviceSelectionNotice }}</small>
      </div>

      <div class="section">
        <div class="section-head">
          <h4>Observaciones</h4>
          <button class="btn-add circle" type="button" @click="addObservacion">
            <img src="/icon_add.png" alt="Agregar" class="icon-add">
          </button>
        </div>
        <div class="field">
          <input v-model="form.observacion" placeholder="Ej: Todos los planes incluyen soporte base" @keyup.enter="addObservacion" />
        </div>
      </div>
    </div>
  </section>
    
</template>

<style scoped>
.cotizador-card {
  width: min(760px, 100%);
  margin: 0 auto;
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(15, 21, 64, 0.14);
  box-shadow: 0 12px 28px rgba(15, 21, 64, 0.07);
  display: flex;
  flex-direction: column;
  padding: clamp(14px, 1.8vw, 20px);
}

.cotizador-card.manual-service-active {
  width: min(860px, 100%);
}

.selection-notice {
  display: block;
  margin-top: 8px;
  color: #8a5a00;
  font-size: 12px;
}

/* header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  gap: 12px;
}
.card-header h3 { margin: 0; color: #1f2b3a; font-size: 17px; font-weight: 700 }
.muted { color: #6b747a; font-size: 12px }

.mode-pill .pill {
  border-radius: 18px;
  border: 1px solid rgba(2, 22, 66, 0.08);
  padding: 6px 12px;
  background: #f6f9fc;
  margin-left: 6px;
  cursor: pointer;
  color: #4b5b68;
  font-size: 12px;
}
.mode-pill .pill.active { background: #00b3ff; color: white; border-color: #00b3ff }

/* body */
.card-body { display: flex; flex-direction: column; gap: 10px }

.config-row { display: flex; gap: 12px; align-items: stretch }
.config-row .section { margin: 0 }
.config-row .section-head {
  min-height: 45px;
  align-items: flex-start;
}
.config-row .section-head h4 {
  line-height: 1.2;
}
.quote-period-section { flex: 0 0 180px }
.config-plan-section { flex: 1 1 auto }
.compact-field input { max-width: 120px }

/* sections */
.section { border: 1px solid rgba(15, 21, 64, 0.08); border-radius: 10px; padding: 10px; background: #fff }
.section h4 { margin: 0 0 6px 0; color: #3e4b58; font-size: 12px; letter-spacing: 0.03em; text-transform: uppercase }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px }

.form-grid { display: grid; grid-template-columns: 1fr; }

.row.two { display: flex; gap: 12px; align-items: flex-start }
.row.two .field { flex: 1 }
.field { display: flex; flex-direction: column; gap: 6px }
.field label { font-size: 12px; color: #6b747a }
.field input,
.field select { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 8px;border: 1px solid rgba(15, 21, 64, 0.24); font-size: 14px; background: #fbfdff;color: black; }

/* items list */
.item {align-items: center;justify-items: center; border: 1px solid rgba(15, 21, 64, 0.08); border-radius: 10px;  background: #f8fbff; padding: 12px }
.svc-main { flex: 1; display: flex; flex-direction: column;}
.svc-main label { font-size: 11px; color: #6b747a }
.svc-name {  width: 100%; padding: 10px 12px;margin: 0 0 10px 0 ; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.24); background: white;color: black;}
.manual-service-input { width: 100%; padding: 10px 12px; margin: 0 0 10px 0; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.24); background: white; color: black; }
.svc-controls { display: flex; gap: 12px; }
.item.manual-service-active .svc-controls { flex-wrap: wrap; }
.mini-field { display: flex; flex-direction: column; gap: 6px; }
.mini-field label { font-size: 11px; color: #6b747a }
.small { width: 90px; padding: 8px; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.24);background-color: transparent;color: black; }
.medium { width: 130px; padding: 8px; border-radius: 8px; border:1px solid rgba(15, 21, 64, 0.24);background-color: transparent;color: black; }
.tiny { width: 68px; padding: 8px; border-radius: 8px; border:1px solid rgba(15, 21, 64, 0.24); text-align: center ;background-color: transparent;color: black;}
.discount-input { display: flex; align-items: center; gap: 6px;color: black; }
.remove { background: white; border: 1px solid rgba(15, 21, 64, 0.08); border-radius: 8px; padding: 7px 9px; cursor: pointer }

/* === UF INFO BOX === */
.uf-info-box {
  margin-top: 10px;
  padding: 12px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(59, 130, 246, 0.08));
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.uf-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4b5b68;
  font-weight: 500;
}

.spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
  font-size: 14px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.uf-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 6px;
  font-size: 12px;
}

.uf-label {
  color: #6b747a;
  font-weight: 500;
}

.uf-value {
  color: #1e40af;
  font-weight: 700;
  font-size: 13px;
}

.uf-converted {
  color: #0f2140;
  font-weight: 600;
  font-size: 13px;
}

/* actions */
.btn-add { background: #08d308; color: white; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 12px }
.icon-add { width: 16px; height: 16px }
.btn-add.circle { width: 28px; height: 28px; padding: 0; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center }

/* footer */
.card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; gap: 12px }
.btn-ghost { background: transparent; border: 1px solid rgba(15, 21, 64, 0.06); padding: 8px 12px; border-radius: 8px; cursor: pointer }
.btn-primary { background: #0073ff; color: white; padding: 10px 14px; border: none; border-radius: 8px; cursor: pointer }

.totals { text-align: right; margin-right: 12px }
.totals .total { margin-top: 6px; font-size: 16px; color: #0073ff }

/* Preview */
.right-panel {
  width: 50%;
  background: #f6f9fc;
  border-left: 1px solid rgba(0,0,0,0.06);
  padding: 20px;
}

.preview-header {
  margin-bottom: 12px;
}

.preview-header h3 {
  margin: 0;
  font-size: 16px;
  color: #1f2b3a;
}

@media (max-width: 720px) {
  .config-row { flex-direction: column; }
  .quote-period-section { flex: 1 1 auto; }
  .compact-field input { max-width: 100%; }
  .row.two { flex-direction: column; }
  .svc-controls { flex-wrap: wrap; }
}
</style>
