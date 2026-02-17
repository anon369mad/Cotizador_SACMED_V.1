<script setup>
import { computed, ref, reactive, onMounted, watch } from 'vue'
import AddOrHist from './Add_or_Hist.vue'
import Preview from './Preview.vue' 
import Parent_Add from './Parent_Add.vue'

const props = defineProps({
  userName: {
    type: String,
    default: 'Usuario'
  },
  userId: {
    type: [String, Number],
    default: null
  }
})

const mode = ref('add') // for demo: 'add' or 'hist'
const currentView = ref('home') // 'home' or 'cotizador'

function handleChange(newMode) {
  mode.value = newMode
}

watch(currentView, (view) => {
  mode.value = view === 'tabs' ? 'hist' : 'add'
}, { immediate: true })

function handleAction(action) {
  if (action === 'add') {
    localStorage.removeItem('cotizador_form_v1')
    const id = Date.now() + Math.random()


    tabs.value.push({
      id,
      title: `Cotización ${tabs.value.length + 1}`,
      data: createEmptyQuote()
    })

    activeTabId.value = id
    currentView.value = 'tabs'
  }

  if (action === 'hist') {
    currentView.value = 'home'
  }
}

const tabs = ref([])
/*
tab = {
  id,
  title,
  data: { ...quote }
}
*/

const activeTabId = ref(null)
function closeTab(id) {
  const idx = tabs.value.findIndex(t => t.id === id)
  if (idx === -1) return

  tabs.value.splice(idx, 1)

  if (activeTabId.value === id) {
    activeTabId.value =
      tabs.value[idx - 1]?.id ||
      tabs.value[0]?.id ||
      null
  }

  if (!tabs.value.length) {
    currentView.value = 'home'
  }
}


function createEmptyQuote() {
  return {
    idUsuario: props.userId != null ? Number(props.userId) : null,
    ejecutivo: props.userName || 'Usuario',
    rut: '',
    name: '',
    connections: 1,
    periodMonths: 3,
    items: [],
    conditions: []
  }
}



function onBack() {
  console.log('Home: onBack called')
  currentView.value = 'home'
}
function logout() {
  // Emitir evento de logout al componente padre (App.vue)
  const event = new CustomEvent('logout')
  window.dispatchEvent(event)
}

const history = ref([])
const isLoadingHistory = ref(false)
const historyError = ref('')
const historySearch = ref('')
const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const prestacionesCache = ref(null)
const planesCache = ref(null)

const filteredHistory = computed(() => {
  const term = historySearch.value.trim().toLowerCase()
  if (!term) return history.value

  return history.value.filter((item) => {
    const searchableFields = [
      item.company,
      item.user,
      item.rut,
      item.plan,
      item.date,
      item.status
    ]

    return searchableFields.some((field) =>
      String(field || '').toLowerCase().includes(term)
    )
  })
})


const draftHistory = computed(() =>
  filteredHistory.value.filter((item) => statusLabel(item.status) !== 'Confirmada')
)

const confirmedHistory = computed(() =>
  filteredHistory.value.filter((item) => statusLabel(item.status) === 'Confirmada')
)

const previewQuote = reactive({
  idUsuario: props.userId != null ? Number(props.userId) : null,
  ejecutivo: props.userName || 'Usuario',
  rut: '',
  name: '—',
  planType: 'Período',
  connections: 1,
  periodMonths: 3,
  items: [],
  conditions: [],
  subtotal: null,
  ivaMonto: null,
  totalMensual: null,
  totalHistorial: null,
  idCotizacion: null,
  estado: null
})

function normalizeDetailItem(detail) {
  return {
    id: detail.id_detalle,
    id_prestacion: detail.id_prestacion ?? null,
    name: detail.descripcion || 'Servicio',
    qty: Number(detail.cantidad || 0),
    quantity: Number(detail.cantidad || 0),
    unitValue: Number(detail.valor_unitario || 0),
    value: Number(detail.valor_unitario || 0),
    discountPct: Number(detail.descuento || 0),
    discount: Number(detail.descuento || 0)
  }
}

function parseConditionLines(rawConditions) {
  if (!rawConditions) return []
  return String(rawConditions)
    .split(/\r?\n/)
    .map((entry) => entry.trim())
    .filter(Boolean)
}

function splitConditionLines(rawConditions) {
  return String(rawConditions || '')
    .split(/\r?\n/)
    .map((entry) => entry.trim())
    .filter(Boolean)
}

function normalizePlanType(value) {
  return String(value || '').toUpperCase().includes('UNICA') ? 'Única' : 'Período'
}

function getConditionsFromDetailItem(item, prestaciones = [], planes = []) {
  if (item?.id_prestacion != null) {
    const prestacion = prestaciones.find(
      (entry) => Number(entry.id_prestacion) === Number(item.id_prestacion)
    )

    if (!prestacion) return []

    return splitConditionLines(prestacion.condiciones).map((text) => ({
      text,
      source: 'service',
      itemId: item.id,
      serviceName: prestacion.nombre || item.name || 'Servicio asociado'
    }))
  }

  const itemName = String(item?.name || '').toLowerCase()
  for (const plan of planes) {
    const planName = String(plan?.nombre || '').trim()
    if (!planName) continue
    if (!itemName.includes(planName.toLowerCase())) continue

    return splitConditionLines(plan.condiciones).map((text) => ({
      text,
      source: 'service',
      itemId: item.id,
      serviceName: planName
    }))
  }

  return []
}

function buildPreviewConditions(rawConditions, detailItems, prestaciones = [], planes = []) {
  const serviceConditions = []
  const serviceTextSet = new Set()

  for (const item of detailItems) {
    const itemConditions = getConditionsFromDetailItem(item, prestaciones, planes)
    for (const condition of itemConditions) {
      const key = `${String(condition.itemId)}::${condition.text.toLowerCase()}`
      if (serviceTextSet.has(key)) continue
      serviceTextSet.add(key)
      serviceConditions.push(condition)
    }
  }

  const serviceOnlyText = new Set(
    serviceConditions.map((condition) => condition.text.toLowerCase())
  )

  const manualConditions = splitConditionLines(rawConditions)
    .filter((condition) => !serviceOnlyText.has(condition.toLowerCase()))
    .map((text) => ({
      text,
      source: 'manual',
      itemId: null,
      serviceName: null
    }))

  return [...serviceConditions, ...manualConditions]
}

async function getPrestaciones() {
  if (Array.isArray(prestacionesCache.value)) {
    return prestacionesCache.value
  }

  const response = await fetch(`${apiBaseUrl}/prestaciones`)
  if (!response.ok) {
    throw new Error('No se pudieron cargar las prestaciones para duplicar la cotización')
  }

  const prestaciones = await response.json()
  prestacionesCache.value = Array.isArray(prestaciones) ? prestaciones : []
  return prestacionesCache.value
}

async function getPlanes() {
  if (Array.isArray(planesCache.value)) {
    return planesCache.value
  }

  const response = await fetch(`${apiBaseUrl}/planes`)
  if (!response.ok) {
    throw new Error('No se pudieron cargar los planes para duplicar la cotización')
  }

  const planes = await response.json()
  planesCache.value = Array.isArray(planes) ? planes : []
  return planesCache.value
}

function extractManualConditions(rawConditions, detailItems, prestaciones = [], planes = []) {
  const allConditions = splitConditionLines(rawConditions)
  if (!allConditions.length) return []

  const serviceConditionKeys = new Set()
  const conditionsByPrestacion = new Map(
    prestaciones.map((prestacion) => [
      Number(prestacion.id_prestacion),
      splitConditionLines(prestacion.condiciones)
    ])
  )

  for (const item of detailItems) {
    const itemConditions = conditionsByPrestacion.get(Number(item?.id_prestacion)) || []
    for (const condition of itemConditions) {
      serviceConditionKeys.add(condition.toLowerCase())
    }

    if (item?.id_prestacion != null) continue

    const itemName = String(item?.name || '').toLowerCase()
    for (const plan of planes) {
      const planName = String(plan?.nombre || '').trim()
      if (!planName) continue
      if (!itemName.includes(planName.toLowerCase())) continue

      for (const condition of splitConditionLines(plan?.condiciones)) {
        serviceConditionKeys.add(condition.toLowerCase())
      }
    }
  }

  return allConditions.filter((condition) => !serviceConditionKeys.has(condition.toLowerCase()))
}

async function fetchQuoteDetails(idCotizacion) {
  const response = await fetch(`${apiBaseUrl}/cotizacion_detalles`)
  if (!response.ok) {
    throw new Error('No se pudieron cargar los detalles de la cotización')
  }

  const detalles = await response.json()
  return (Array.isArray(detalles) ? detalles : [])
    .filter((detail) => Number(detail.id_cotizacion) === Number(idCotizacion))
    .map(normalizeDetailItem)
}

async function selectHistory(h){
  historyError.value = ''
  previewQuote.idUsuario = h.idUsuario ?? null
  previewQuote.ejecutivo = h.user || 'Usuario'
  previewQuote.name = h.company
  previewQuote.rut = h.rut || ''
  previewQuote.planType = normalizePlanType(h.plan)
  previewQuote.connections = h.connections || 0
  previewQuote.periodMonths = h.periods || 6
  previewQuote.items = []
  previewQuote.conditions = []
  previewQuote.subtotal = h.subtotal ?? null
  previewQuote.ivaMonto = h.ivaMonto ?? null
  previewQuote.totalMensual = h.totalMensual ?? null
  previewQuote.totalHistorial = h.price ?? null
  previewQuote.idCotizacion = h.id
  previewQuote.estado = h.status

  try {
    const [detailItems, prestaciones, planes] = await Promise.all([
      fetchQuoteDetails(h.id),
      getPrestaciones(),
      getPlanes()
    ])

    previewQuote.items = detailItems
    previewQuote.conditions = buildPreviewConditions(h.rawConditions, detailItems, prestaciones, planes)
  } catch (error) {
    historyError.value = error instanceof Error
      ? error.message
      : 'Error inesperado al cargar detalles del historial'
  }
}

function formatMoney(v){ return '$' + Number(v).toLocaleString('es-CL') }

watch(
  () => [props.userId, props.userName],
  ([newUserId, newUserName]) => {
    const normalizedUserId = newUserId != null ? Number(newUserId) : null
    if (!previewQuote.idUsuario) {
      previewQuote.idUsuario = normalizedUserId
    }
    if (!previewQuote.ejecutivo || previewQuote.ejecutivo === 'Usuario') {
      previewQuote.ejecutivo = newUserName || 'Usuario'
    }
  },
  { immediate: true }
)

watch(
  () => props.userId,
  () => {
    loadHistory()
  }
)


function statusLabel(status){
  if (!status) return 'Borrador'
  const normalized = status.toString().toLowerCase()
  if (normalized.includes('confirm')) return 'Confirmada'
  return 'Borrador'
}

function statusClass(status){
  return statusLabel(status) === 'Confirmada' ? 'confirmed' : 'draft'
}

function formatDate(value){
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

function toNumber(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function getHistoryTotal(item) {
  const monthlyTotal = toNumber(item.total)
  const months = Math.max(1, toNumber(item.meses, 1))
  const isUniquePlan = String(item.tipo || '').toUpperCase().includes('UNICA')
  return isUniquePlan ? monthlyTotal : monthlyTotal * months
}

function mapHistoryItem(item){
  return {
    id: item.id_cotizacion,
    company: item.nombre_cliente || 'Cliente sin nombre',
    idUsuario: item.id_usuario ?? null,
    user: item.nombre_usuario || `Usuario #${item.id_usuario}`,
    rut: item.rut_cliente || '',
    date: formatDate(item.fecha_emision),
    plan: item.tipo || '—',
    connections: item.conexiones || 0,
    periods: toNumber(item.meses, 6),
    price: getHistoryTotal(item),
    subtotal: toNumber(item.subtotal, 0),
    ivaMonto: toNumber(item.iva_monto, 0),
    totalMensual: toNumber(item.total, 0),
    items: [],
    conditions: parseConditionLines(item.condiciones_adicionales),
    rawConditions: item.condiciones_adicionales || '',
    status: item.estado
  }
}

async function deleteHistoryQuote(h) {
  try {
    const response = await fetch(`${apiBaseUrl}/cotizaciones/${h.id}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error('No se pudo eliminar la cotización del historial')
    }

    await loadHistory()

    if (previewQuote.idCotizacion === h.id) {
      Object.assign(previewQuote, {
        idCotizacion: null,
        estado: null,
        name: '—',
        rut: '',
        planType: 'Período',
        items: [],
        conditions: []
      })
    }
  } catch (error) {
    historyError.value = error instanceof Error
      ? error.message
      : 'Error inesperado al eliminar cotización'
  }
}

async function duplicateQuote(h){
  historyError.value = ''

  try {
    const detailItems = await fetchQuoteDetails(h.id)
    const [prestaciones, planes] = await Promise.all([
      getPrestaciones(),
      getPlanes()
    ])
    const id = Date.now() + Math.random()

    tabs.value.push({
      id,
      title: `Cotización ${tabs.value.length + 1}`,
      data: {
        idUsuario: h.idUsuario ?? null,
        ejecutivo: h.user,
        rut: h.rut || '',
        name: h.company,
        connections: h.connections || 0,
        periodMonths: h.periods || 6,
        items: detailItems,
        conditions: extractManualConditions(h.rawConditions, detailItems, prestaciones, planes),
        idCotizacion: null,
        estado: null
      }
    })

    activeTabId.value = id
    currentView.value = 'tabs'
  } catch (error) {
    historyError.value = error instanceof Error
      ? error.message
      : 'Error inesperado al duplicar la cotización'
  }
}

async function editDraftQuote(h) {
  if (statusLabel(h.status) === 'Confirmada') return

  historyError.value = ''
  try {
    const detailItems = await fetchQuoteDetails(h.id)
    const [prestaciones, planes] = await Promise.all([
      getPrestaciones(),
      getPlanes()
    ])
    const id = Date.now() + Math.random()

    tabs.value.push({
      id,
      title: `Borrador ${h.company}`,
      data: {
        idCotizacion: h.id,
        estado: h.status,
        idUsuario: h.idUsuario ?? null,
        ejecutivo: h.user,
        rut: h.rut || '',
        name: h.company,
        cliente: h.company,
        planType: normalizePlanType(h.plan),
        connections: h.connections || 0,
        conexiones: h.connections || 0,
        periodMonths: h.periods || 6,
        items: detailItems,
        conditions: extractManualConditions(h.rawConditions, detailItems, prestaciones, planes),
        condiciones: extractManualConditions(h.rawConditions, detailItems, prestaciones, planes)
      }
    })

    activeTabId.value = id
    currentView.value = 'tabs'
  } catch (error) {
    historyError.value = error instanceof Error
      ? error.message
      : 'Error inesperado al preparar la edición del borrador'
  }
}

async function loadHistory(){
  isLoadingHistory.value = true
  historyError.value = ''
  try {
    const normalizedUserId = props.userId != null ? Number(props.userId) : null
    if (normalizedUserId == null || Number.isNaN(normalizedUserId)) {
      history.value = []
      return
    }

    const params = new URLSearchParams({
      id_usuario: String(normalizedUserId)
    })
    const response = await fetch(`${apiBaseUrl}/cotizaciones?${params.toString()}`)
    if (!response.ok) {
      throw new Error('No se pudo cargar el historial de cotizaciones')
    }
    const data = await response.json()
    history.value = (Array.isArray(data) ? data : []).map(mapHistoryItem)
    console.log('Historial cargado:', history.value)
  } catch (error) {
    historyError.value = error instanceof Error
      ? error.message
      : 'Error inesperado al cargar el historial'
  } finally {
    isLoadingHistory.value = false
  }
}


function openConfirmedView() {
  currentView.value = 'confirmed'
}

function returnToDraftsView() {
  currentView.value = 'home'
}

async function handleQuoteFinalized() {
  await loadHistory()
  currentView.value = 'confirmed'
}

onMounted(() => {
  previewQuote.idUsuario = props.userId != null ? Number(props.userId) : null
  previewQuote.ejecutivo = props.userName || 'Usuario'
  loadHistory()
})
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div class="topbar-left">
        <h2 class="brand">Sistema de Cotizaciones</h2>
        <div class="subtitle">Panel De</div>
      </div>
      <div class="topbar-right">
        <div class="user">
          <span class="user-icon">👤</span>
          <span class="user-name">{{ userName }}</span>
        </div>
        <button class="btn-exit" @click="logout">
          <span class="exit-icon">🚪</span>
          <span class="exit-text">Salir</span>
        </button>
      </div>
    </header>
     <div v-if="currentView === 'tabs'" class="tabs-bar">

  <div
    v-for="t in tabs"
    :key="t.id"
    class="tab"
    :class="{ active: t.id === activeTabId }"
    @click="activeTabId = t.id"
  >
    {{ t.title }}
    <span class="close" @click.stop="closeTab(t.id)">✕</span>
  </div>

  <!-- BOTÓN NUEVA PESTAÑA -->
  <div
    class="tab add-tab"
    @click="handleAction('add')"
  >
    +
  </div>

</div>

    <main
       class="container-home"
        :class="{ 'container-parent': currentView === 'parentAdd' }"
        >
      <template v-if="currentView === 'home'">
        <section class="main-area">
          <div class="hist-card">
            <h4>Borradores en Cotizador</h4>
            <input
              v-model="historySearch"
              class="search"
              placeholder="Buscar por cliente o ejecutivo..."
            />

            <div v-if="isLoadingHistory" class="list-empty">Cargando historial...</div>
            <div v-else-if="historyError" class="list-empty error">{{ historyError }}</div>
            <div v-else-if="!draftHistory.length" class="list-empty">
              {{ history.length ? 'No se encontraron borradores para la búsqueda.' : 'No hay borradores registrados.' }}
            </div>
            <ul v-else class="list">
              <li class="list-item" v-for="h in draftHistory" :key="h.id">
                <div class="list-left">
                  <div class="company">{{ h.company }}</div>
                  <div class="meta">{{ h.user }} · {{ h.date }}<br/><small>{{ h.plan }} · {{ h.connections }} conexiones</small></div>
                  <div class="list-actions">
                    <button class="action-btn" type="button" @click="selectHistory(h)">Visualizar</button>
                    <button
                      v-if="statusLabel(h.status) !== 'Confirmada'"
                      class="action-btn"
                      type="button"
                      @click="editDraftQuote(h)"
                    >Editar borrador</button>
                    <button class="action-btn secondary" type="button" @click="duplicateQuote(h)">Duplicar</button>
                    <button
                      v-if="statusLabel(h.status) !== 'Confirmada'"
                      class="action-btn danger"
                      type="button"
                      @click="deleteHistoryQuote(h)"
                    >Eliminar borrador</button>
                  </div>
                </div>
                <div class="list-right">
                  <div class="status" :class="statusClass(h.status)">{{ statusLabel(h.status) }}</div>
                  <div class="price">{{ formatMoney(h.price) }}</div>
                </div>
              </li>
            </ul>
            <button class="action-btn secondary" type="button" @click="openConfirmedView">Ver cotizaciones confirmadas</button>
          </div>
          <aside class="sidebar">
            <Preview :quote="previewQuote" />
          </aside>
        </section>
      </template>

      
      <template v-if="currentView === 'confirmed'">
        <section class="main-area">
          <div class="hist-card">
            <h4>Cotizaciones confirmadas</h4>
            <input
              v-model="historySearch"
              class="search"
              placeholder="Buscar confirmadas..."
            />

            <div v-if="isLoadingHistory" class="list-empty">Cargando historial...</div>
            <div v-else-if="historyError" class="list-empty error">{{ historyError }}</div>
            <div v-else-if="!confirmedHistory.length" class="list-empty">
              No hay cotizaciones confirmadas para mostrar.
            </div>
            <ul v-else class="list">
              <li class="list-item" v-for="h in confirmedHistory" :key="h.id">
                <div class="list-left">
                  <div class="company">{{ h.company }}</div>
                  <div class="meta">{{ h.user }} · {{ h.date }}<br/><small>{{ h.plan }} · {{ h.connections }} conexiones</small></div>
                  <div class="list-actions">
                    <button class="action-btn" type="button" @click="selectHistory(h)">Visualizar</button>
                    <button class="action-btn secondary" type="button" @click="duplicateQuote(h)">Duplicar</button>
                    <button
                      class="action-btn danger"
                      type="button"
                      @click="deleteHistoryQuote(h)"
                    >Eliminar confirmada</button>
                  </div>
                </div>
                <div class="list-right">
                  <div class="status" :class="statusClass(h.status)">{{ statusLabel(h.status) }}</div>
                  <div class="price">{{ formatMoney(h.price) }}</div>
                </div>
              </li>
            </ul>
            <button class="action-btn" type="button" @click="returnToDraftsView">Volver a borradores</button>
          </div>
          <aside class="sidebar">
            <Preview :quote="previewQuote" />
          </aside>
        </section>
      </template>

<template v-if="currentView === 'tabs'">
  <section class="main-area main-area--tabs">
    <Parent_Add
  :key="activeTabId"
  :quote="tabs.find(t => t.id === activeTabId)?.data"
  :tab-id="activeTabId"
  @back="currentView = 'home'"
  @history-changed="loadHistory"
  @quote-finalized="handleQuoteFinalized"
/>


  </section>
</template>

    </main>

    <AddOrHist :initial="mode" position="left" @change="handleChange" @action="handleAction" />
  </div>
</template>

<style scoped>
.page {
  background: white;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  background: white;
  color: #0f2140;
  padding: 10px clamp(14px, 3vw, 28px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(15, 21, 64, 0.146);
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 20;
}

.brand { margin: 0; font-size: clamp(16px, 2vw, 18px); color: #003366; }
.subtitle { font-size: 12px; color: rgba(15,21,64,0.5); }
.topbar-left { display: flex; flex-direction: column; }
.topbar-right { display: flex; align-items: center; gap: 10px; }
.topbar-right .user {
  background: linear-gradient(135deg, rgba(26,163,255,0.08), rgba(2,22,66,0.04));
  padding: 8px 12px;
  border-radius: 20px;
  color: #0f2140;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 200px;
  border: 1px solid rgba(26,163,255,0.15);
  transition: all 0.2s ease;
}
.topbar-right .user:hover {
  background: linear-gradient(135deg, rgba(26,163,255,0.12), rgba(2,22,66,0.06));
  border-color: rgba(26,163,255,0.25);
}
.user-icon {
  font-size: 16px;
  min-width: 16px;
}
.user-name {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.btn-exit {
  background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
  border: none;
  padding: 8px 14px;
  border-radius: 20px;
  color: white;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(255,107,107,0.2);
}
.btn-exit:hover {
  background: linear-gradient(135deg, #ff5252, #dd4e63);
  box-shadow: 0 4px 12px rgba(255,107,107,0.3);
  transform: translateY(-1px);
}
.exit-icon {
  font-size: 16px;
}
.exit-text {
  line-height: 1;
}

.container-home {
  display: flex;
  flex: 1;
  width: 100%;
  justify-content: center;
  padding: clamp(12px, 2.5vw, 24px) clamp(12px, 4vw, 72px);
}

.main-area {
  display: grid;
  grid-template-columns: minmax(320px, 520px) minmax(320px, 1fr);
  align-items: start;
  gap: clamp(16px, 2vw, 24px);
  width: min(1100px, 100%);
}

.hist-card {
  width: 100%;
  background: white;
  border-radius: 10px;
  padding: 18px;
  border: 1px solid rgba(15, 21, 64, 0.146);
  box-shadow: 0 2px 8px rgba(2, 22, 66, 0.03);
}

.hist-card h4 { text-align: left; margin: 0 0 12px; color: #003366; font-weight: 600; }
.search {
  width: 100%;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid rgba(15, 21, 64, 0.146);
  margin-bottom: 14px;
  background: white;
}

.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px;
  background: rgba(114, 226, 243, 0.372);
  border-radius: 8px;
  border: 1px solid rgba(15,21,64,0.03);
  gap: 12px;
}
.company { font-size: 12px; font-weight: 600; color: #155a52; }
.meta { color: #6b747a; font-size: 11px; }
.list-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.action-btn {
  border: 1px solid rgba(15,21,64,0.12);
  background: white;
  color: #0f2140;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
}
.action-btn.secondary { background: transparent; color: #0f2140; }
.action-btn.danger { background: #fee2e2; color: #b91c1c; border-color: #fecaca; }
.action-btn.danger:hover { background: #fecaca; }
.list-empty { font-size: 12px; color: #6b747a; padding: 12px 4px; }
.list-empty.error { color: #c0392b; }
.status { padding: 4px 8px; border-radius: 12px; font-size: 12px; white-space: nowrap; }
.status.confirmed { background: #1fb800; color: #ffffff; }
.status.draft { background: #ffb300; color: #ffffff; }
.price { color: #0073ff; font-weight: 700; text-align: right; }

.sidebar {
  width: 100%;
  min-width: 0;
}

.tabs-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px 0;
  border-bottom: 1px solid #e6eef7;
  overflow-x: auto;
  white-space: nowrap;
}

.tab {
  padding: 10px 14px;
  background: transparent;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
  font-size: 14px;
  color: #6b7280;
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  user-select: none;
}
.tab.active { color: #0f2140; font-weight: 600; }
.tab.active::after {
  content: '';
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: -1px;
  height: 3px;
  background: #1aa3ff;
  border-radius: 4px;
}
.add-tab {
  font-weight: 700;
  color: #93a0ab;
  min-width: 36px;
  text-align: center;
  padding: 8px 10px;
}
.tab:hover { background: rgba(2, 22, 66, 0.02); }
.close { margin-left: 8px; cursor: pointer; opacity: 0.6; font-size: 12px; line-height: 1; }
.close:hover { opacity: 1; }
.tabs-bar::-webkit-scrollbar { height: 6px; }
.tabs-bar::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.06); border-radius: 4px; }

@media (max-width: 1024px) {
  .main-area {
    grid-template-columns: 1fr;
  }

  .sidebar {
    order: -1;
  }
}

@media (max-width: 720px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .topbar-right {
    width: 100%;
    justify-content: space-between;
  }

  .list-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .list-right {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .tab { padding: 8px 12px; font-size: 13px; }
  .add-tab { min-width: 30px; padding: 6px 8px; }
}
</style>
