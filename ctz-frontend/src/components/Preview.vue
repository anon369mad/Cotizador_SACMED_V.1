<template>
  <div class="preview-wrapper">
    <div class="paper" ref="paper">
      <header class="paper-header">
        <img src="/sacmed.png" alt="logo" class="logo" />
        <div>
          <h2>Empresa - Cotización</h2>
          <div class="meta">Ejecutivo: {{ quote.ejecutivo || 'Usuario' }}</div>
        </div>
      </header>

      <section class="paper-section">
        <h3>Datos del Cliente</h3>
        <div class="two-cols">
          <div><strong>RUT</strong><div>{{ quote.rut || '—' }}</div></div>
          <div><strong>Nombre</strong><div>{{ quote.name || '—' }}</div></div>
        </div>
      </section>

      <section class="paper-section">
        <h3>Servicios</h3>
        <table class="items">
          <thead>
            <tr><th>Servicio</th><th>Cant.</th><th>Unitario</th><th>Desc</th><th>Subtotal</th></tr>
          </thead>
          <tbody>
            <tr v-for="(it, i) in quote.items || []" :key="i">
              <td>{{ it.name }}</td>
              <td>{{ it.quantity }}</td>
              <td class="mono">{{ formatMoney(it.value) }}</td>
              <td>{{ it.discount }}%</td>
              <td class="mono">{{ formatMoney(lineTotal(it)) }}</td>
            </tr>
          </tbody>
        </table>

        <div class="totals">
          <div><span>Subtotal</span><span class="mono">{{ formatMoney(subtotal) }}</span></div>
          <div><span>IVA (19%)</span><span class="mono">{{ formatMoney(iva) }}</span></div>
          <div class="total"><span>Total</span><span class="mono">{{ formatMoney(total) }}</span></div>
        </div>
      </section>

      <section class="paper-section small">
        <h3>Condiciones</h3>
        <ul>
          <li v-for="(c, i) in (quote.conditions || [])" :key="i">{{ c }}</li>
          <li v-if="!(quote.conditions && quote.conditions.length)">—</li>
        </ul>
      </section>

      <footer class="paper-footer">Documento generado (vista preliminar)</footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
const props = defineProps({
  quote: { type: Object, default: () => ({
    ejecutivo: 'Usuario',
    rut: '',
    name: '',
    connections: 0,
    periodMonths: 6,
    items: [],
    conditions: []
  }) }
})

const paper = ref(null)

function formatMoney(v){ return '$' + Number(v || 0).toLocaleString('es-CL') }
function lineTotal(it){ return Math.round(it.quantity * it.value * (1 - (it.discount||0)/100)) }

const subtotal = computed(() => (props.quote.items || []).reduce((s, it) => s + lineTotal(it), 0))
const iva = computed(() => Math.round(subtotal.value * 0.19))
const total = computed(() => subtotal.value + iva.value)

function printPreview(){
  const printWindow = window.open('', '_blank', 'noopener')
  if (!printWindow) return
  const html = `
    <html>
      <head>
        <title>Cotización</title>
        <style>
          body{font-family:Inter, Arial, sans-serif; margin:0; padding:20px; background:#f0f0f0}
          .paper{width:210mm; min-height:297mm; margin:0 auto; background:white; padding:28mm; box-shadow:0 0 0 1px rgba(0,0,0,0.06)}
          h2,h3{margin:0 0 6px 0}
          .two-cols{display:flex; gap:24px}
          table{width:100%; border-collapse:collapse; margin-top:8px}
          th,td{padding:8px; border-bottom:1px solid #eee; text-align:left}
          .totals{margin-top:12px; width:100%; display:flex; flex-direction:column; gap:6px}
          .totals div{display:flex; justify-content:space-between}
          .total{font-weight:700}
          .mono{font-family:monospace}
        </style>
      </head>
      <body>
        ${paper.value ? paper.value.innerHTML : '<div>Vista no disponible</div>'}
      </body>
    </html>
  `
  printWindow.document.write(html)
  printWindow.document.close()
  // delay to ensure styles/images load
  setTimeout(()=>printWindow.print(), 250)
}
</script>

<style scoped>
.preview-wrapper { display:flex; flex-direction:column; gap:12px }
.toolbar { display:flex; gap:8px; justify-content:flex-end }
.btn { background:#1ca4ff; color:white; border:none; padding:8px 12px; border-radius:6px; cursor:pointer }
.btn.muted { background:transparent; color:#1ca4ff; border:1px solid rgba(28,164,255,0.2) }

.paper { background:white; border-radius:4px; box-shadow: 0 6px 18px rgba(2,22,66,0.06); padding:18px; overflow:hidden }
.paper-header { display:flex; gap:12px; align-items:center }
.paper-header .logo{ width:60px; height:auto }
.paper-section { margin-top:16px }
.items th{ font-weight:600 }
.totals{ margin-top:12px }
.totals .mono{ font-family:monospace }
.paper-footer{ margin-top:24px; font-size:12px; color:#667 }

/* small page simulation sizing for screen */
.paper{ max-width:900px }
</style>
