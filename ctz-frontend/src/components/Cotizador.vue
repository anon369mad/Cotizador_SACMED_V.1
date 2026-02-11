<script setup>
import { reactive, computed, watch, ref, onMounted } from 'vue'

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

const STORAGE_KEY = computed(() => `cotizador_form_${props.tabId}`)
const defaultForm = {
  ejecutivo: '',
  cliente: '',
  rut: '',
  planType: 'Período',
  periodMonths: 6,
  conexiones: 1,
  condicion:'',
  condiciones: [],
  cantidad: 1,
  valor: 0,
  descuento: 0,
  seleccionado: '',
  manualServiceName: '',
  items: []
}

const MANUAL_SERVICE_OPTION = '__manual_service__'

function normalizeInitialData(data) {
  if (!data) return {}
  return {
    ...data,
    ejecutivo: data.ejecutivo ?? data.user ?? '',
    cliente: data.cliente ?? data.name ?? '',
    conexiones: data.conexiones ?? data.connections ?? 1,
    condiciones: data.condiciones ?? data.conditions ?? '',
    items: Array.isArray(data.items)
      ? JSON.parse(JSON.stringify(data.items))
      : []
  }
}

const savedForm = localStorage.getItem(STORAGE_KEY.value)
const initialForm = {
  ...structuredClone(defaultForm),
  ...normalizeInitialData(props.initialData),
  ...(savedForm ? JSON.parse(savedForm) : {})
}

const form = reactive(initialForm)


const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const prestaciones = ref([])
const prestacionesLoading = ref(false)
const prestacionesError = ref('')
const planes = ref([])
const planesLoading = ref(false)
const planesError = ref('')

function formatMoney(v) {
  return '$' + Number(v || 0).toLocaleString('es-CL')
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
  const Seleccionada = prestaciones.value.find(
    (it) => it.id_prestacion === Number(form.seleccionado)
  )
  const condicionServicio = String(Seleccionada.condiciones || '').trim()
  if (condicionServicio && !form.condiciones.includes(condicionServicio)) {
    form.condiciones.push(condicionServicio)
  }
  if (!form.seleccionado) return
  
  if (form.planType === 'Única' && form.seleccionado === MANUAL_SERVICE_OPTION) {
    const manualName = String(form.manualServiceName || '').trim()
    if (!manualName) return

    form.items.push({
      id: Date.now(),
      name: manualName,
      qty: form.cantidad,
      unitValue: form.valor,
      discountPct: form.descuento,
      condiciones: null,
      source: 'manual'
    })

    form.seleccionado = ''
    form.manualServiceName = ''
    form.cantidad = 1
    form.valor = 0
    form.descuento = 0
    return
  }

  const prestacionSeleccionada = prestaciones.value.find(
    (it) => it.id_prestacion === Number(form.seleccionado)
  )

  if (!prestacionSeleccionada) return

  form.items.push({
    id: Date.now(),
    id_prestacion: prestacionSeleccionada.id_prestacion,
    name: prestacionSeleccionada.nombre,
    qty: form.cantidad,
    unitValue: form.valor,
    discountPct: form.descuento,
    condiciones: prestacionSeleccionada.condiciones || null,
    source: 'db'
  })

  // Limpiar inputs
  form.seleccionado = ''
  form.manualServiceName = ''
  form.cantidad = 1
  form.valor = 0
  form.descuento = 0

}
function addCondicion() {
  const condicion = String(form.condicion || '').trim()
  if (!condicion) return
  form.condiciones.push(condicion)
  form.condicion = ''

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
  if (form.planType === 'Única' || !planes.value.length) {
    form.items = manualItems
    return
  }

  const conexionesSolicitadas = Math.max(0, Number(form.conexiones || 0))
  const planBase = [...planes.value]
    .reverse()
    .find((it) => Number(it.conexiones_incluidas || 0) <= conexionesSolicitadas)
    ?? planes.value[0]
  if (!planBase) {
    form.items = manualItems
    return
  }

  const conexionesIncluidas = Number(planBase.conexiones_incluidas || 0)
  const conexionesExtra = Math.max(0, conexionesSolicitadas - conexionesIncluidas)

  const planItems = [{
    id: `auto-plan-${planBase.id_plan}`,
    id_plan: planBase.id_plan,
    name: `${planBase.nombre} (${conexionesIncluidas} conexiones)`,
    qty: 1,
    unitValue: Number(planBase.valor_plan_mensual || 0),
    discountPct: 0,
    condiciones: planBase.condiciones || null,
    autoPlan: true,
    source: 'db'
  }]

  if (conexionesExtra > 0) {
    planItems.push({
      id: `auto-plan-extra-${planBase.id_plan}`,
      name: `Conexiones extra (${planBase.nombre})`,
      qty: conexionesExtra,
      unitValue: Number(planBase.valor_conexion_adicional || 0),
      discountPct: 0,
      autoPlan: true,
      source: 'db'
    })
  }

  form.items = [...planItems, ...manualItems]
}

function onSelectPrestacion() {
  if (form.seleccionado === MANUAL_SERVICE_OPTION) {
    form.valor = 0
    return
  }

  const prestacionSeleccionada = prestaciones.value.find(
    (it) => it.id_prestacion === Number(form.seleccionado)
  )

  if (!prestacionSeleccionada) return

  form.valor = Number(prestacionSeleccionada.valor_unitario || 0)
}

onMounted(() => {
  cargarPrestaciones()
  cargarPlanes()
})

const subtotal = computed(() =>
  form.items.reduce((sum, it) => {
    return sum + it.qty * it.unitValue * (1 - it.discountPct / 100)
  }, 0)
)

const iva = computed(() => Math.round(subtotal.value * 0.19))
const total = computed(() => subtotal.value + iva.value)

function buildPreview() {
  return {
    ejecutivo: form.ejecutivo,
    cliente: form.cliente,
    rut: form.rut,

    planType: form.planType,
    periodMonths: form.periodMonths,
    conexiones: form.conexiones,
    condiciones: form.condiciones,

    items: form.items,
  }
}

watch(form, () => {
  emit('update-preview', buildPreview())
}, { deep: true, immediate: true })

watch(
  [() => form.conexiones, () => form.planType, planes],
  () => {
    syncPlanItems()
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
  <section class="cotizador-card">
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
      <div class="form-grid">
        <div class="section">
          <h4>Datos del cliente</h4>
          <div class="row two">
            <div class="field">
              <label>RUT Persona/Empresa *</label>
             <input
              v-model="form.rut"
              placeholder="Ej: 12.345.678-5"
              @input="formatRut"
              maxlength="12"
              required/>
              <small v-if="rutError" class="error">
                RUT inválido
              </small>

            </div>
            <div class="field">
              <label>Nombre/Razón Social *</label>
              <input v-model="form.cliente" placeholder="Ej: Empresa ABC Ltda." required/>
            </div>
          </div>
        </div>

        <div class="section" v-if="form.planType === 'Período'">
          <h4>Configuración del servicio</h4>
          <div class="row two">
            <div class="field">
              <label>Cantidad de Conexiones</label>
              <input type="number" min="0" v-model.number="form.conexiones" />
              <small v-if="planesLoading">Cargando planes...</small>
              <small v-else-if="planesError" class="error">{{ planesError }}</small>
            </div>
            <div class="field">
              <label>Período de Contratación (meses)</label>
              <input type="number" min="1" v-model.number="form.periodMonths" />
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
          <div class="item">
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
                <label>Valor</label>
                <input type="number" min="0" class="medium" v-model.number="form.valor" />
              </div>
              <div class="mini-field">
                <label>Descuento</label>
                <div class="discount-input">
                  <input type="number" min="0" max="100" class="tiny" v-model.number="form.descuento" />
                  <span>%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-head">
          <h4>Condiciones adicionales</h4>
          <button class="btn-add circle">
            <img src="/icon_add.png" alt="Agregar" class="icon-add" @click="addCondicion">
          </button>
        </div>
        <div class="field">
          <input v-model="form.condicion" placeholder="Ej: capacitación: costo $0" />
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

/* header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  gap: 12px;
}
.card-header h3 { margin: 0; color: #1f2b3a; font-size: 20px; font-weight: 700 }
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
.mode-pill .pill.active { background: #0f4c81; color: white; border-color: #0f4c81 }

/* body */
.card-body { display: flex; flex-direction: column; gap: 12px }

/* sections */
.section { border: 1px solid rgba(15, 21, 64, 0.08); border-radius: 10px; padding: 12px; background: #fff }
.section h4 { margin: 0 0 8px 0; color: #3e4b58; font-size: 13px; letter-spacing: 0.04em; text-transform: uppercase }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px }

.form-grid { display: grid; grid-template-columns: 1fr; }

.row.two { display: flex; gap: 12px }
.field { display: flex; flex-direction: column; gap: 6px }
.field label { font-size: 12px; color: #6b747a }
.field input { padding: 10px 12px; border-radius: 8px;border: 1px solid rgba(15, 21, 64, 0.24); font-size: 14px; background: #fbfdff;color: black; }

/* items list */
.item {align-items: center;justify-items: center; border: 1px solid rgba(15, 21, 64, 0.08); border-radius: 10px;  background: #f8fbff; padding: 12px }
.svc-main { flex: 1; display: flex; flex-direction: column;}
.svc-main label { font-size: 11px; color: #6b747a }
.svc-name {  width: 100%; padding: 10px 12px;margin: 0 0 10px 0 ; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.24); background: white;color: black;}
.manual-service-input { width: 100%; padding: 10px 12px; margin: 0 0 10px 0; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.24); background: white; color: black; }
.svc-controls { display: flex; gap: 12px; }
.mini-field { display: flex; flex-direction: column; gap: 6px; }
.mini-field label { font-size: 11px; color: #6b747a }
.small { width: 90px; padding: 8px; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.24);background-color: transparent;color: black; }
.medium { width: 130px; padding: 8px; border-radius: 8px; border:1px solid rgba(15, 21, 64, 0.24);background-color: transparent;color: black; }
.tiny { width: 68px; padding: 8px; border-radius: 8px; border:1px solid rgba(15, 21, 64, 0.24); text-align: center ;background-color: transparent;color: black;}
.discount-input { display: flex; align-items: center; gap: 6px;color: black; }
.remove { background: white; border: 1px solid rgba(15, 21, 64, 0.08); border-radius: 8px; padding: 7px 9px; cursor: pointer }

/* actions */
.btn-add { background: #0f4c81; color: white; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 12px }
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
  .row.two { flex-direction: column; }
  .svc-controls { flex-wrap: wrap; }
}
</style>
