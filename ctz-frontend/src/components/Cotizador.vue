<script setup>
import { reactive, computed, watch } from 'vue'
const emit = defineEmits(['back', 'update-preview'])

const form = reactive({
  ejecutivo: 'Carolina',
  cliente: '',
  rut: '',
  planType: 'Período',
  periodMonths: 6,
  conexiones: 1,
  observaciones: '',
  items: [
    { id: 1, name: 'CotizadorX', qty: 1, unitValue: 900000, discountPct: 0 }
  ]
})

/* util */
function formatMoney(v) { return '$' + Number(v).toLocaleString('es-CL') }

/* items y totales */
const subtotal = computed(() => {
  return form.items.reduce((s, it) => {
    const val = Number(it.unitValue) || 0
    const q = Number(it.qty) || 0
    const disc = Number(it.discountPct) || 0
    const line = q * val * (1 - disc / 100)
    return s + line
  }, 0)
})
const iva = computed(() => Math.round(subtotal.value * 0.19))
const total = computed(() => subtotal.value + iva.value)

/* funciones de UI */
function addItem() {
  const id = Date.now()
  form.items.push({ id, name: 'Nuevo servicio', qty: 1, unitValue: 0, discountPct: 0 })
}
function removeItem(id) {
  const idx = form.items.findIndex(i => i.id === id)
  if (idx >= 0) form.items.splice(idx, 1)
}
function onBackClick() { emit('back') }
function submit() {
  // aquí iría la lógica real de guardar
  console.log('Enviar cotización', JSON.parse(JSON.stringify(form)))
  emit('update-preview', buildPreview())
}

/* construye el objeto que el preview usará */
function buildPreview() {
  const items = form.items.map(it => ({
    name: it.name,
    qty: Number(it.qty) || 0,
    unit: Number(it.unitValue) || 0,
    discount: Number(it.discountPct) || 0,
    total: Math.round((Number(it.qty) || 0) * (Number(it.unitValue) || 0) * (1 - (Number(it.discountPct) || 0) / 100))
  }))
  return {
    ejecutivo: form.ejecutivo,
    name: form.cliente || '—',
    rut: form.rut || '—',
    connections: Number(form.conexiones) || 0,
    periodMonths: Number(form.periodMonths) || 6,
    items,
    subtotal: Math.round(subtotal.value),
    iva: Math.round(iva.value),
    total: Math.round(total.value),
    issuedAt: new Date().toLocaleString(),
    dueAt: ''
  }
}

watch(form, () => {
  emit('update-preview', buildPreview())
}, { deep: true, immediate: true })
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
              <input v-model="form.rut" placeholder="Ej: 76.123.456-7" />
            </div>
            <div class="field">
              <label>Nombre / Razón Social *</label>
              <input v-model="form.cliente" placeholder="Ej: Empresa ABC Ltda." />
            </div>
          </div>
        </div>

        <div class="section">
          <h4>Configuración del servicio</h4>
          <div class="row two">
            <div class="field">
              <label>Cantidad de Conexiones</label>
              <input type="number" min="0" v-model.number="form.conexiones" />
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
          <button class="btn-add" type="button" @click="addItem()">+ Agregar servicio</button>
        </div>

        <div class="items-list">
          <div class="item" v-for="it in form.items" :key="it.id">
            <div class="svc-main">
              <label>Servicio</label>
              <input class="svc-name" v-model="it.name" placeholder="Ej: CotizadorX" />
            </div>
            <div class="svc-controls">
              <div class="mini-field">
                <label>Cantidad</label>
                <input type="number" min="0" class="small" v-model.number="it.qty" />
              </div>
              <div class="mini-field">
                <label>Valor</label>
                <input type="number" min="0" class="medium" v-model.number="it.unitValue" />
              </div>
              <div class="mini-field">
                <label>Descuento</label>
                <div class="discount-input">
                  <input type="number" min="0" max="100" class="tiny" v-model.number="it.discountPct" />
                  <span>%</span>
                </div>
              </div>
              <button class="remove" @click="removeItem(it.id)" type="button">✕</button>
            </div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-head">
          <h4>Condiciones adicionales</h4>
          <button class="btn-add circle" type="button">+</button>
        </div>
        <div class="field">
          <input v-model="form.observaciones" placeholder="Ej: capacitación: costo $0" />
        </div>
      </div>
    </div>

    <div class="card-footer">
      <div class="right-actions">
        <div class="totals">
          <div>Subtotal: <strong>{{ formatMoney(subtotal) }}</strong></div>
          <div>IVA (19%): <strong>{{ formatMoney(iva) }}</strong></div>
        </div>
    </div>
    </div>
  </section>
</template>

<style scoped>
.cotizador-card {
  background: white;
  border-radius: 12px;
  border: 1px solid rgba(15, 21, 64, 0.08);
  padding: 22px 24px;
  box-shadow: 0 10px 30px rgba(12, 38, 70, 0.04);
  max-width: 450px;
  display: flex;
  flex-direction: column;   
}

/* header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.card-header h3 { margin: 0; color: #1f2b3a; font-size: 18px }
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
.mode-pill .pill.active { background: #00a3f0; color: white }

/* body */
.card-body { display: flex; flex-direction: column; gap: 14px }

/* sections */
.section { border: 1px solid rgba(15, 21, 64, 0.06); border-radius: 10px; padding: 14px 16px; background: #fff }
.section h4 { margin: 0 0 8px 0; color: #3e4b58; font-size: 13px; letter-spacing: 0.04em; text-transform: uppercase }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px }

.form-grid { display: grid; grid-template-columns: 1fr; gap: 14px }

.row.two { display: flex; gap: 12px }
.field { display: flex; flex-direction: column; gap: 6px }
.field label { font-size: 12px; color: #6b747a }
.field input { padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.08); font-size: 14px; background: #fbfdff;color: black; }

/* items list */
.item { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: flex-end; border: 1px solid rgba(15, 21, 64, 0.06); border-radius: 10px; padding: 10px 12px; background: #f8fbff }
.svc-main { flex: 1; display: flex; flex-direction: column; gap: 6px }
.svc-main label { font-size: 11px; color: #6b747a }
.svc-name { width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.08); background: white;color: black }
.svc-controls { display: flex; gap: 10px; flex-direction: column;}
.mini-field { display: flex; flex-direction: column; gap: 6px }
.mini-field label { font-size: 11px; color: #6b747a }
.small { width: 72px; padding: 8px; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.08) }
.medium { width: 120px; padding: 8px; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.08) }
.tiny { width: 56px; padding: 8px; border-radius: 8px; border: 1px solid rgba(15, 21, 64, 0.08); text-align: center }
.discount-input { display: flex; align-items: center; gap: 6px }
.remove { background: white; border: 1px solid rgba(15, 21, 64, 0.08); border-radius: 8px; padding: 7px 9px; cursor: pointer }

/* actions */
.btn-add { background: #00c853; color: white; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 12px }
.btn-add.circle { width: 28px; height: 28px; padding: 0; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center }

/* footer */
.card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; gap: 12px }
.btn-ghost { background: transparent; border: 1px solid rgba(15, 21, 64, 0.06); padding: 8px 12px; border-radius: 8px; cursor: pointer }
.btn-primary { background: #0073ff; color: white; padding: 10px 14px; border: none; border-radius: 8px; cursor: pointer }

.totals { text-align: right; margin-right: 12px }
.totals .total { margin-top: 6px; font-size: 16px; color: #0073ff }

/*@media (max-width: 980px) {
  .cotizador-card { max-width: 100% }
  .form-grid { grid-template-columns: 1fr }
  .item { flex-direction: column; align-items: stretch }
  .svc-controls { flex-wrap: wrap }
  .card-footer { flex-direction: column; align-items: flex-start }
  .totals { text-align: left; margin-right: 0 }
}*/
</style>
