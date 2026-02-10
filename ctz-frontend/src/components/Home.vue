<script setup>
import { ref, reactive, onMounted } from 'vue'
import AddOrHist from './Add_or_Hist.vue'
import Preview from './Preview.vue' 
import Parent_Add from './Parent_Add.vue'

defineProps({
  userName: {
    type: String,
    default: 'Usuario'
  }
})

const mode = ref('add') // for demo: 'add' or 'hist'
const currentView = ref('home') // 'home' or 'cotizador'

function handleChange(newMode) {
  mode.value = newMode
}

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
    ejecutivo: 'Carolina',
    rut: '',
    name: '',
    connections: 0,
    periodMonths: 6,
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
const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const previewQuote = reactive({
  ejecutivo: 'Usuario',
  rut: '',
  name: '—',
  connections: 0,
  periodMonths: 6,
  items: [],
  conditions: []
})

function selectHistory(h){
  previewQuote.name = h.company
  previewQuote.rut = ''
  previewQuote.connections = h.connections || 0
  previewQuote.periodMonths = h.periods || 6
  previewQuote.items = JSON.parse(JSON.stringify(h.items || []))
  previewQuote.conditions = JSON.parse(JSON.stringify(h.conditions || []))
}

function formatMoney(v){ return '$' + Number(v).toLocaleString('es-CL') }

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

function mapHistoryItem(item){
  return {
    id: item.id_cotizacion,
    company: `Cliente #${item.id_cliente}`,
    user: `Usuario #${item.id_usuario}`,
    date: formatDate(item.fecha_emision),
    plan: item.tipo || '—',
    connections: item.conexiones || 0,
    periods: item.meses || 6,
    price: item.total || 0,
    items: [],
    conditions: item.condiciones_adicionales
      ? [item.condiciones_adicionales]
      : [],
    status: item.estado
  }
}

function duplicateQuote(h){
  const id = Date.now() + Math.random()
  tabs.value.push({
    id,
    title: `Cotización ${tabs.value.length + 1}`,
    data: {
      ejecutivo: h.user,
      rut: '',
      name: h.company,
      connections: h.connections || 0,
      periodMonths: h.periods || 6,
      items: JSON.parse(JSON.stringify(h.items || [])),
      conditions: JSON.parse(JSON.stringify(h.conditions || []))
    }
  })
  activeTabId.value = id
  currentView.value = 'tabs'
}

async function loadHistory(){
  isLoadingHistory.value = true
  historyError.value = ''
  try {
    const response = await fetch(`${apiBaseUrl}/cotizaciones`)
    if (!response.ok) {
      throw new Error('No se pudo cargar el historial de cotizaciones')
    }
    const data = await response.json()
    history.value = (Array.isArray(data) ? data : []).map(mapHistoryItem)
  } catch (error) {
    historyError.value = error instanceof Error
      ? error.message
      : 'Error inesperado al cargar el historial'
  } finally {
    isLoadingHistory.value = false
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div class="topbar-left">
        <h2 class="brand">Sistema de Cotizaciones</h2>
        <div class="subtitle">Panel</div>
      </div>
      <div class="topbar-right">
        <div class="user">{{ userName }}</div>
        <button class="btn-exit" @click="logout">Salir</button>
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
            <h4>Historial de Cotizaciones</h4>
            <input class="search" placeholder="Buscar por cliente o ejecutivo..." />

            <div v-if="isLoadingHistory" class="list-empty">Cargando historial...</div>
            <div v-else-if="historyError" class="list-empty error">{{ historyError }}</div>
            <div v-else-if="!history.length" class="list-empty">No hay cotizaciones registradas.</div>
            <ul v-else class="list">
              <li class="list-item" v-for="h in history" :key="h.id">
                <div class="list-left">
                  <div class="company">{{ h.company }}</div>
                  <div class="meta">{{ h.user }} · {{ h.date }}<br/><small>{{ h.plan }} · {{ h.connections }} conexiones</small></div>
                  <div class="list-actions">
                    <button class="action-btn" type="button" @click="selectHistory(h)">Visualizar</button>
                    <button class="action-btn secondary" type="button" @click="duplicateQuote(h)">Duplicar</button>
                  </div>
                </div>
                <div class="list-right">
                  <div class="status" :class="statusClass(h.status)">{{ statusLabel(h.status) }}</div>
                  <div class="price">{{ formatMoney(h.price) }}</div>
                </div>
              </li>
            </ul>
          </div>
          <aside class="sidebar">
            <Preview :quote="previewQuote" />
          </aside>
        </section>
      </template>

      <template v-if="currentView === 'tabs'">
  <section class="main-area">
    <Parent_Add
  :key="activeTabId"
  :quote="tabs.find(t => t.id === activeTabId)?.data"
  :tab-id="activeTabId"
  @back="currentView = 'home'"
/>


  </section>
</template>

    </main>

    <AddOrHist initial="add" position="left" @change="handleChange" @action="handleAction" />
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
  background: rgba(2,22,66,0.04);
  padding: 6px 10px;
  border-radius: 16px;
  color: #0f2140;
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.btn-exit {
  background: transparent;
  border: 1px solid rgba(15,21,64,0.15);
  padding: 6px 10px;
  border-radius: 6px;
  color: #0f2140;
  cursor: pointer;
}
.btn-exit:hover { background: rgba(2,22,66,0.04); }

.container-home {
  display: flex;
  flex: 1;
  width: 100%;
  padding: clamp(12px, 2.5vw, 24px) clamp(12px, 4vw, 86px);
}

.main-area {
  display: grid;
  grid-template-columns: minmax(320px, 520px) minmax(320px, 1fr);
  align-items: start;
  gap: clamp(16px, 2vw, 24px);
  width: 100%;
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
