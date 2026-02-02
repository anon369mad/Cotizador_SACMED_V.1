<script setup>
import { ref, reactive } from 'vue'
import AddOrHist from './Add_or_Hist.vue'
import Cotizador from './Cotizador.vue'
import Preview from './Preview.vue' 

const mode = ref('add') // for demo: 'add' or 'hist'
const currentView = ref('home') // 'home' or 'cotizador'

function handleChange(newMode) {
  mode.value = newMode
}

function handleAction(action) {
  // action = 'add' | 'hist' based on which icon was clicked
  if (action === 'add') {
    currentView.value = 'cotizador'
  } else if (action === 'hist') {
    currentView.value = 'home'
  }
}

function onBack() {
  console.log('Home: onBack called')
  currentView.value = 'home'
}
function logout() {
  // replace with real logout logic when available
  console.log('logout clicked')
}

// sample historial seleccionable
const history = ref([
  { company: 'Empresa Star', user: 'Carolina', date: '19-01-2026, 09:52 a. m.', plan:'Plan 5', connections:1, price:59500, items:[{name:'Plan 5', quantity:1, value:59500, discount:0}], conditions:[] },
  { company: 'Empresa Luna', user: 'Carolina', date: '18-01-2026, 08:12 a. m.', plan:'Plan 4', connections:2, price:45000, items:[{name:'Plan 4', quantity:2, value:22500, discount:0}], conditions:[] },
  { company: 'Empresa Sol', user: 'Carolina', date: '17-01-2026, 10:20 a. m.', plan:'Plan 3', connections:4, price:120000, items:[{name:'Plan 3', quantity:4, value:30000, discount:0}], conditions:[] }
])

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
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div class="topbar-left">
        <h2 class="brand">Sistema de Cotizaciones</h2>
        <div class="subtitle">Panel</div>
      </div>
      <div class="topbar-right">
        <div class="user">Carolina</div>
        <button class="btn-exit" @click="logout">Salir</button>
      </div>
    </header>

    <main
      class="container"
      :class="{ single: currentView === 'cotizador' }"
    >
      <template v-if="currentView === 'home'">
        <section class="main-area">
          <div class="hist-card">
            <h4>Historial de Cotizaciones</h4>
            <input class="search" placeholder="Buscar por cliente o ejecutivo..." />

            <ul class="list">
              <li class="list-item" v-for="(h,i) in history" :key="i" @click="selectHistory(h)">
                <div class="list-left">
                  <div class="company">{{ h.company }}</div>
                  <div class="meta">{{ h.user }} · {{ h.date }}<br/><small>{{ h.plan }} · {{ h.connections }} conexiones</small></div>
                </div>
                <div class="list-right">
                  <div class="status confirmed">Confirmada</div>
                  <div class="price">{{ formatMoney(h.price) }}</div>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <aside class="sidebar">
          <Preview :quote="previewQuote" />
        </aside>
      </template>

      <template v-else>
        <section class="main-area">
         <Cotizador @back="onBack" />
        </section>
         <aside class="sidebar">
          <Preview :quote="previewQuote" />
        </aside>
      </template>
    </main>

    <AddOrHist initial="add" position="left" @change="handleChange" @action="handleAction" />
  </div>
</template>

<style>
.page {
  background: white; /* plain white background */
  flex-direction: column;
}

/* topbar is white with a subtle divider line */
.topbar {
  background: white;
  color: #0f2140;
  padding: 8px 28px; /* moved up with smaller padding */
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(15, 21, 64, 0.146);
  /*position: sticky; /* keep on top */
  top: 0;
  z-index: 20;
}

.brand { margin: 0; font-size: 18px; color: #003366 }
.subtitle { font-size: 12px; color: rgba(15,21,64,0.5); }
.topbar-left { display:flex; flex-direction:column;padding-left: 10px; }
.topbar-right { display:flex; align-items:center; gap:10px; padding-bottom:8px; padding-right: 10px; }
.topbar-right .user { background: rgba(2,22,66,0.04); padding:6px 10px; border-radius:16px; color:#0f2140 }
.btn-exit { background: transparent; border: 1px solid rgba(15,21,64,0.08); padding:6px 10px; border-radius:6px; color:#0f2140; cursor:pointer }
.btn-exit:hover { background: rgba(2,22,66,0.04) }

.container {
  display: grid;
  grid-template-columns: 1fr 420px;
  padding: 16px 86px; /* reduce padding so content fits without scroll */
  align-items: center; /* center columns vertically */
  flex: 0.1; /* make it fill remaining vertical space */
  /*min-height: calc(100vh - 56px); /* leave room for topbar */
}

.main-area { display:flex; justify-content:center; align-items:center; }

.hist-card {
  width: 420px; /* slightly narrower to feel more centered */
  margin: 0; /* ensure centering inside column */
  background: white; /* always white */
  border-radius: 8px;
  padding: 18px;
  border: 1px solid rgba(15, 21, 64, 0.146); /* soft border */
  box-shadow: 0 2px 8px rgba(2, 22, 66, 0.03);
}

.hist-card h4 { text-align: left;margin: 0 0 12px 0; color:#003366; font-weight:600 }
.search { width:90%; padding:10px 12px; border-radius:6px; border:1px solid rgba(15, 21, 64, 0.146); margin-bottom:14px; background:white; }

.list { list-style:none; padding: 0; margin:0; display:flex; flex-direction:column; gap:10px; }
.list-item { display:flex; justify-content:space-between; align-items:center; padding:14px; background:rgba(114, 226, 243, 0.372); border-radius:6px; border:1px solid rgba(15,21,64,0.03); }
.company { font-size:12px; font-weight:600; color:#155a52; }
.meta { color:#6b747a; font-size:10px }
.status { padding:4px 8px; border-radius:12px; font-size:12px; }
.status.confirmed { background:#1fb800; color:#ffffff; }
.status.processing { background:#ffb300; color:#ffffff; }
.price { color:#0073ff; font-weight:700 }

.preview-card { background:white; border-radius:8px; /*padding:18px;*/ box-shadow: 0 2px 8px rgba(2,22,66,0.04); }
.tag { font-size:12px; display:inline-block; padding:6px 8px; border-radius:12px; color:white }
.tag.confirmed { background:#00d18a }
.preview-body { margin-top:12px }
.row { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #f0f3f5 }
.row.total { font-weight:700; color:#0073ff }
.service-box { background:#f7f9fb; padding:8px; margin:12px 0; border-radius:6px }
.service-row { display:flex; justify-content:space-between; padding:6px 0 }

/* responsive */
/*@media (max-width: 960px) {
  .container { grid-template-columns: 1fr; }
  .hist-card { width: 100%; }
  .topbar { padding: 12px 18px }
}*/
</style> 
    