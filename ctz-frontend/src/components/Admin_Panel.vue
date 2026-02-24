<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

const props = defineProps({
  userName: {
    type: String,
    default: 'Administrador'
  },
  userRole: {
    type: String,
    default: ''
  },
  userId: {
    type: [String, Number],
    default: null
  }
})

const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const activeTab = ref('usuarios')
const isLoading = ref(false)
const feedback = ref('')
const feedbackType = ref('success')

const users = ref([])
const plans = ref([])
const services = ref([])
const platformTrainingRules = ref([])
const ivaConfig = ref([])
const additionalServicesPdf = ref({ has_file: false, filename: null, uploaded_at: null })
const additionalServicesFile = ref(null)
const isUploadingAdditionalPdf = ref(false)

const userSearch = ref('')

const userModal = ref({ open: false, mode: 'create', id: null })
const userForm = reactive({
  nombre: '',
  email: '',
  rol: 'SALES_USER',
  activo: true
})

const planModal = ref({ open: false, mode: 'create', type: 'plan', id: null })
const planForm = reactive({
  nombre: '',
  conexiones_incluidas: 1,
  valor_plan_mensual: 0,
  valor_conexion_adicional: 0,
  valor_unitario: 0,
  condiciones: '',
  activo: true,
  clp: true,
  mensajes_whatsapp: 0
})
const platformTrainingModal = ref({ open: false, mode: 'create', id: null })
const platformTrainingCollapsed = ref(true)
const platformTrainingForm = reactive({
  conexiones_desde: 1,
  conexiones_hasta: null,
  horas_capacitacion: 0
})

const ivaForm = reactive({
  id_iva: null,
  nombre: 'IVA',
  porcentaje: 19,
  activo: true
})
const ivaEditMode = ref(false)
const ivaDraft = reactive({
  nombre: 'IVA',
  porcentaje: 19,
  activo: true
})

const isAdmin = computed(() => String(props.userRole || '').toUpperCase() === 'ADMIN')

const filteredUsers = computed(() => {
  const term = userSearch.value.trim().toLowerCase()
  if (!term) return users.value
  return users.value.filter((user) =>
    [user.nombre, user.email, user.rol].some((field) =>
      String(field || '').toLowerCase().includes(term)
    )
  )
})


function resetFeedback() {
  feedback.value = ''
}

function showFeedback(message, type = 'success') {
  feedback.value = message
  feedbackType.value = type
}

async function request(endpoint, options = {}) {
  const response = await fetch(`${apiBaseUrl}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    },
    ...options
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || 'Ocurrió un error al procesar la solicitud')
  }

  if (response.status === 204) return null
  return response.json().catch(() => null)
}

async function loadUsers() {
  users.value = await request('/usuarios')
}

async function loadPrices() {
  const [allPlans, allServices, allPlatformTrainingRules] = await Promise.all([
    request('/planes'),
    request('/prestaciones'),
    request('/capacitaciones-plataforma')
  ])
  plans.value = Array.isArray(allPlans) ? allPlans : []
  services.value = Array.isArray(allServices) ? allServices : []
  platformTrainingRules.value = Array.isArray(allPlatformTrainingRules) ? allPlatformTrainingRules : []
}

async function loadIva() {
  const allIva = await request('/iva')
  ivaConfig.value = Array.isArray(allIva)
    ? [...allIva].sort((a, b) => Number(b?.id_iva || 0) - Number(a?.id_iva || 0))
    : []

  if (ivaConfig.value.length) {
    const current = ivaConfig.value.find((entry) => entry?.activo) || ivaConfig.value[0]
    ivaForm.id_iva = current.id_iva
    ivaForm.nombre = current.nombre || 'IVA'
    ivaForm.porcentaje = Number(current.porcentaje || 0)
    ivaForm.activo = current.activo !== false
    syncIvaDraft()
  } else {
    ivaForm.id_iva = null
    ivaForm.nombre = 'IVA'
    ivaForm.porcentaje = 19
    ivaForm.activo = true
    syncIvaDraft()
  }

  ivaEditMode.value = false
}

function syncIvaDraft() {
  ivaDraft.nombre = ivaForm.nombre
  ivaDraft.porcentaje = Number(ivaForm.porcentaje || 0)
  ivaDraft.activo = ivaForm.activo
}

function startIvaEdit() {
  syncIvaDraft()
  ivaEditMode.value = true
  resetFeedback()
}

function cancelIvaEdit() {
  syncIvaDraft()
  ivaEditMode.value = false
  resetFeedback()
}

async function loadData() {
  if (!isAdmin.value) return

  isLoading.value = true
  resetFeedback()
  try {
    await Promise.all([loadUsers(), loadPrices(), loadIva(), loadAdditionalServicesPdf()])
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo cargar el panel', 'error')
  } finally {
    isLoading.value = false
  }
}

function logout() {
  const event = new CustomEvent('logout')
  window.dispatchEvent(event)
}

function openCreateUser() {
  userModal.value = { open: true, mode: 'create', id: null }
  Object.assign(userForm, {
    nombre: '',
    email: '',
    rol: 'SALES_USER',
    activo: true
  })
}

function openEditUser(user) {
  userModal.value = { open: true, mode: 'edit', id: user.id_usuario }
  Object.assign(userForm, {
    nombre: user.nombre || '',
    email: user.email || '',
    rol: user.rol || 'SALES_USER',
    activo: user.activo !== false
  })
}

function closeUserModal() {
  userModal.value = { open: false, mode: 'create', id: null }
}

async function submitUser() {
  resetFeedback()

  if (!userForm.nombre.trim() || !userForm.email.trim()) {
    showFeedback('Nombre y correo son obligatorios', 'error')
    return
  }


  const payload = {
    nombre: userForm.nombre.trim(),
    email: userForm.email.trim(),
    rol: userForm.rol,
    activo: userForm.activo
  }


  try {
    if (userModal.value.mode === 'create') {
      await request('/usuarios', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
      showFeedback('Usuario creado correctamente. Se envió un código de validación al correo del usuario')
    } else {
      await request(`/usuarios/${userModal.value.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      })
      showFeedback('Usuario actualizado correctamente')
    }

    await loadUsers()
    closeUserModal()
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo guardar el usuario', 'error')
  }
}

async function deleteUser(user) {
  if (Number(user.id_usuario) === Number(props.userId)) {
    showFeedback('No puedes eliminar tu propio usuario administrador', 'error')
    return
  }

  const confirmed = window.confirm(`¿Eliminar al usuario ${user.nombre}?`)
  if (!confirmed) return

  try {
    await request(`/usuarios/${user.id_usuario}`, { method: 'DELETE' })
    showFeedback('Usuario eliminado correctamente')
    await loadUsers()
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo eliminar el usuario', 'error')
  }
}

function openCreatePrice(type) {
  planModal.value = { open: true, mode: 'create', type, id: null }
  Object.assign(planForm, {
    nombre: '',
    conexiones_incluidas: 1,
    valor_plan_mensual: 0,
    valor_conexion_adicional: 0,
    valor_unitario: 0,
    condiciones: '',
    activo: true,
    clp: true,
    mensajes_whatsapp: 0
  })
}

function openEditPrice(type, entry) {
  planModal.value = {
    open: true,
    mode: 'edit',
    type,
    id: type === 'plan' ? entry.id_plan : entry.id_prestacion
  }

  Object.assign(planForm, {
    nombre: entry.nombre || '',
    conexiones_incluidas: Number(entry.conexiones_incluidas || 1),
    valor_plan_mensual: Number(entry.valor_plan_mensual || 0),
    valor_conexion_adicional: Number(entry.valor_conexion_adicional || 0),
    valor_unitario: Number(entry.valor_unitario || 0),
    condiciones: entry.condiciones || '',
    activo: entry.activo !== false,
    clp: entry.clp !== false,
    mensajes_whatsapp: Number(entry.mensajes_whatsapp || 0)
  })
}

function closePriceModal() {
  planModal.value = { open: false, mode: 'create', type: 'plan', id: null }
}

async function submitPrice() {
  resetFeedback()

  if (!planForm.nombre.trim()) {
    showFeedback('El nombre es obligatorio', 'error')
    return
  }

  try {
    if (planModal.value.type === 'plan') {
      const payload = {
        nombre: planForm.nombre.trim(),
        conexiones_incluidas: Number(planForm.conexiones_incluidas || 0),
        valor_plan_mensual: Number(planForm.valor_plan_mensual || 0),
        valor_conexion_adicional: Number(planForm.valor_conexion_adicional || 0),
        condiciones: planForm.condiciones,
        activo: planForm.activo,
        mensajes_whatsapp: Number(planForm.mensajes_whatsapp || 0)
      }

      const endpoint = planModal.value.mode === 'create'
        ? '/planes'
        : `/planes/${planModal.value.id}`
      const method = planModal.value.mode === 'create' ? 'POST' : 'PUT'

      await request(endpoint, {
        method,
        body: JSON.stringify(payload)
      })
    } else {
      const payload = {
        nombre: planForm.nombre.trim(),
        valor_unitario: Number(planForm.valor_unitario || 0),
        condiciones: planForm.condiciones,
        activo: planForm.activo,
        clp: planForm.clp
      }

      const endpoint = planModal.value.mode === 'create'
        ? '/prestaciones'
        : `/prestaciones/${planModal.value.id}`
      const method = planModal.value.mode === 'create' ? 'POST' : 'PUT'

      await request(endpoint, {
        method,
        body: JSON.stringify(payload)
      })
    }

    await loadPrices()
    const baseMessage = planModal.value.mode === 'create' ? 'Registro creado correctamente' : 'Registro actualizado correctamente'
    showFeedback(baseMessage)
    closePriceModal()
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo guardar la información', 'error')
  }
}

async function deletePrice(type, entry) {
  const label = type === 'plan' ? entry.nombre : `servicio ${entry.nombre}`
  if (!window.confirm(`¿Eliminar ${label}?`)) return

  try {
    const endpoint = type === 'plan' ? `/planes/${entry.id_plan}` : `/prestaciones/${entry.id_prestacion}`
    await request(endpoint, { method: 'DELETE' })
    showFeedback('Registro eliminado correctamente')
    await loadPrices()
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo eliminar el registro', 'error')
  }
}

function formatTrainingInterval(rule) {
  if (rule.conexiones_hasta == null) {
    return `${rule.conexiones_desde}+ conexiones`
  }
  return `${rule.conexiones_desde} a ${rule.conexiones_hasta} conexiones`
}

function togglePlatformTraining() {
  platformTrainingCollapsed.value = !platformTrainingCollapsed.value
}

function openCreatePlatformTrainingRule() {
  platformTrainingModal.value = { open: true, mode: 'create', id: null }
  Object.assign(platformTrainingForm, {
    conexiones_desde: 1,
    conexiones_hasta: null,
    horas_capacitacion: 0
  })
}

function openEditPlatformTrainingRule(rule) {
  platformTrainingModal.value = { open: true, mode: 'edit', id: rule.id_capacitacion_plataforma }
  Object.assign(platformTrainingForm, {
    conexiones_desde: Number(rule.conexiones_desde || 1),
    conexiones_hasta: rule.conexiones_hasta == null ? null : Number(rule.conexiones_hasta),
    horas_capacitacion: Number(rule.horas_capacitacion || 0)
  })
}

function closePlatformTrainingModal() {
  platformTrainingModal.value = { open: false, mode: 'create', id: null }
}

async function submitPlatformTrainingRule() {
  resetFeedback()

  const desde = Number(platformTrainingForm.conexiones_desde || 0)
  const hasta = platformTrainingForm.conexiones_hasta == null || platformTrainingForm.conexiones_hasta === ''
    ? null
    : Number(platformTrainingForm.conexiones_hasta)
  const horas = Number(platformTrainingForm.horas_capacitacion || 0)

  if (desde < 1) {
    showFeedback('El inicio del intervalo debe ser mayor o igual a 1', 'error')
    return
  }

  if (hasta !== null && hasta < desde) {
    showFeedback('El fin del intervalo debe ser mayor o igual al inicio', 'error')
    return
  }

  if (horas < 0) {
    showFeedback('Las horas de capacitación no pueden ser negativas', 'error')
    return
  }

  try {
    const payload = {
      conexiones_desde: desde,
      conexiones_hasta: hasta,
      horas_capacitacion: horas
    }

    const endpoint = platformTrainingModal.value.mode === 'create'
      ? '/capacitaciones-plataforma'
      : `/capacitaciones-plataforma/${platformTrainingModal.value.id}`
    const method = platformTrainingModal.value.mode === 'create' ? 'POST' : 'PUT'

    await request(endpoint, {
      method,
      body: JSON.stringify(payload)
    })

    await loadPrices()
    showFeedback(platformTrainingModal.value.mode === 'create' ? 'Relación creada correctamente' : 'Relación actualizada correctamente')
    closePlatformTrainingModal()
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo guardar la relación', 'error')
  }
}

async function deletePlatformTrainingRule(rule) {
  if (!window.confirm(`¿Eliminar la relación ${formatTrainingInterval(rule)} / ${rule.horas_capacitacion} horas?`)) return

  try {
    await request(`/capacitaciones-plataforma/${rule.id_capacitacion_plataforma}`, { method: 'DELETE' })
    showFeedback('Relación eliminada correctamente')
    await loadPrices()
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo eliminar la relación', 'error')
  }
}

async function loadAdditionalServicesPdf() {
  additionalServicesPdf.value = await request('/configuraciones/servicios-adicionales')
}

function onAdditionalServicesPdfChange(event) {
  const [file] = event?.target?.files || []
  additionalServicesFile.value = file || null
}

async function uploadAdditionalServicesPdf() {
  resetFeedback()

  if (!additionalServicesFile.value) {
    showFeedback('Selecciona un archivo PDF para subir', 'error')
    return
  }

  if (!String(additionalServicesFile.value.name || '').toLowerCase().endsWith('.pdf')) {
    showFeedback('Solo se permiten archivos con extensión .pdf', 'error')
    return
  }

  isUploadingAdditionalPdf.value = true
  try {
    const formData = new FormData()
    formData.append('file', additionalServicesFile.value)

    const response = await fetch(`${apiBaseUrl}/configuraciones/servicios-adicionales`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(payload?.detail || 'No se pudo subir el PDF')
    }

    additionalServicesFile.value = null
    const fileInput = document.getElementById('additional-services-pdf')
    if (fileInput) fileInput.value = ''

    await loadAdditionalServicesPdf()
    showFeedback('PDF de servicios adicionales actualizado correctamente')
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo subir el PDF', 'error')
  } finally {
    isUploadingAdditionalPdf.value = false
  }
}


async function submitIva() {
  resetFeedback()
  try {
    const payload = {
      nombre: ivaDraft.nombre.trim() || 'IVA',
      porcentaje: Number(ivaDraft.porcentaje || 0),
      activo: ivaDraft.activo
    }

    if (ivaForm.id_iva) {
      const updated = await request(`/iva/${ivaForm.id_iva}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      })
      ivaForm.id_iva = updated?.id_iva ?? ivaForm.id_iva
    } else {
      const created = await request('/iva', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
      ivaForm.id_iva = created?.id_iva ?? null
    }

    showFeedback('IVA actualizado correctamente')
    await loadIva()
    ivaEditMode.value = false
  } catch (error) {
    showFeedback(error instanceof Error ? error.message : 'No se pudo actualizar el IVA', 'error')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="admin-page">
    <header class="topbar">
      <div>
        <h2>Panel de Administración</h2>
        <p>Gestión de precios y reglas comerciales</p>
      </div>
      <div class="topbar-user">
        <div class="admin-user-pill">
          <span class="admin-user-icon" aria-hidden="true">👤</span>
          <span class="admin-user-name">{{ userName }}</span>
        </div>
        <button class="admin-exit-btn" type="button" @click="logout">
          <img src="/sign-out-option.png" alt="" class="admin-exit-icon" aria-hidden="true" />
          <span>Salir</span>
        </button>
      </div>
    </header>

    <main class="content">
      <div v-if="!isAdmin" class="card empty-state">
        Esta vista solo está disponible para el rol administrador.
      </div>

      <template v-else>
        <div class="tab-row" role="tablist" aria-label="Secciones de administración">
          <button
            class="tab"
            :class="{ active: activeTab === 'usuarios' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'usuarios'"
            @click="activeTab = 'usuarios'"
          >
            <span class="tab-icon" aria-hidden="true">👥</span>
            <span>Usuarios</span>
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'precios' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'precios'"
            @click="activeTab = 'precios'"
          >
            <span class="tab-icon" aria-hidden="true">$</span>
            <span>Precios</span>
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'iva' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'iva'"
            @click="activeTab = 'iva'"
          >
            <span class="tab-icon" aria-hidden="true">%</span>
            <span>IVA</span>
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'serviciosPdf' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'serviciosPdf'"
            @click="activeTab = 'serviciosPdf'"
          >
            <span class="tab-icon" aria-hidden="true">📎</span>
            <span>Servicios PDF</span>
          </button>
        </div>

        <p v-if="feedback" class="feedback" :class="feedbackType">{{ feedback }}</p>
        <div v-if="isLoading" class="card empty-state">Cargando panel administrativo...</div>

        <section v-else-if="activeTab === 'usuarios'" class="card">
          <div class="section-header">
            <h3>Gestión de usuarios</h3>
            <button class="btn-primary add-price-btn" type="button" @click="openCreateUser">+ Nuevo usuario</button>
          </div>
          <input v-model="userSearch" class="search" placeholder="Buscar por nombre o correo..." />

          <div v-if="!filteredUsers.length" class="empty-state">No hay usuarios para mostrar.</div>
          <ul v-else class="entity-list">
            <li v-for="user in filteredUsers" :key="user.id_usuario" class="entity-row">
              <div>
                <strong>{{ user.nombre }}</strong>
                <p>{{ user.email }}</p>
                <small>{{ user.rol === 'ADMIN' ? 'Administrador' : 'Usuario' }} · {{ user.activo ? 'Activo' : 'Inactivo' }}</small>
              </div>
              <div class="actions">
                <button class="icon-btn" type="button" @click="openEditUser(user)">✏️</button>
                <button class="icon-btn danger" type="button" @click="deleteUser(user)">🗑️</button>
              </div>
            </li>
          </ul>
        </section>

        <section v-else-if="activeTab === 'precios'" class="card">
          <div class="prices-grid">
            <section class="prices-section">
              <div class="section-header prices-header">
                <h3>Planes</h3>
                <button class="btn-primary add-price-btn" type="button" @click="openCreatePrice('plan')">+ Nuevo plan</button>
              </div>
              <ul class="cards-list prices-cards-list">
                <li v-for="plan in plans" :key="plan.id_plan" class="price-card">
                  <h4>{{ plan.nombre }}</h4>
                  <div class="price-field"><span>Conexiones</span><strong>{{ plan.conexiones_incluidas }}</strong></div>
                  <div class="price-field"><span>Plan mensual</span><strong>{{ Number(plan.valor_plan_mensual).toLocaleString('es-CL') }}</strong></div>
                  <div class="price-field"><span>Conexión extra</span><strong>{{ Number(plan.valor_conexion_adicional).toLocaleString('es-CL') }}</strong></div>
                  <div class="price-field"><span>Mensajes WhatsApp</span><strong>{{ Number(plan.mensajes_whatsapp || 0).toLocaleString('es-CL') }}</strong></div>
                  <small>{{ plan.condiciones || 'Sin condiciones' }}</small>
                  <div class="actions">
                    <button class="icon-btn" type="button" @click="openEditPrice('plan', plan)">✏️</button>
                    <button class="icon-btn danger" type="button" @click="deletePrice('plan', plan)">🗑️</button>
                  </div>
                </li>
              </ul>
            </section>

            <section class="prices-section">
              <div class="section-header prices-header">
                <h3>Prestaciones</h3>
                <button class="btn-primary add-price-btn" type="button" @click="openCreatePrice('servicio')">+ Nuevo servicio</button>
              </div>
              <ul class="cards-list prices-cards-list">
                <li v-for="service in services" :key="service.id_prestacion" class="price-card">
                  <h4>{{ service.nombre }}</h4>
                  <div class="price-field"><span>Valor unitario</span><strong>{{ Number(service.valor_unitario || 0).toLocaleString('es-CL') }}</strong></div>
                  <div class="price-field"><span>Tipo moneda</span><strong>{{ service.clp ? 'CLP' : 'UF' }}</strong></div>
                  <small>{{ service.condiciones || 'Sin condiciones' }}</small>
                  <div class="actions">
                    <button class="icon-btn" type="button" @click="openEditPrice('servicio', service)">✏️</button>
                    <button class="icon-btn danger" type="button" @click="deletePrice('servicio', service)">🗑️</button>
                  </div>
                </li>
              </ul>
            </section>

            <section class="prices-section training-section">
              <div class="section-header prices-header collapsible-header">
                <button
                  class="collapse-toggle"
                  type="button"
                  :aria-expanded="!platformTrainingCollapsed"
                  @click="togglePlatformTraining"
                >
                  <h3>Capacitaciones plataforma</h3>
                  <span class="collapse-arrow" :class="{ collapsed: platformTrainingCollapsed }" aria-hidden="true">▾</span>
                </button>
                <button class="btn-primary add-price-btn" type="button" @click="openCreatePlatformTrainingRule">+ Nueva relación</button>
              </div>
              <ul v-show="!platformTrainingCollapsed" class="training-list">
                <li v-for="rule in platformTrainingRules" :key="rule.id_capacitacion_plataforma" class="training-row">
                  <div class="training-data">
                    <strong>{{ formatTrainingInterval(rule) }}</strong>
                    <span>{{ rule.horas_capacitacion }} horas de capacitación</span>
                  </div>
                  <div class="actions">
                    <button class="icon-btn" type="button" @click="openEditPlatformTrainingRule(rule)">✏️</button>
                    <button class="icon-btn danger" type="button" @click="deletePlatformTrainingRule(rule)">🗑️</button>
                  </div>
                </li>
              </ul>
            </section>
          </div>
        </section>

        <section v-else-if="activeTab === 'iva'" class="iva-tab-panel">
          <div class="card iva-card">
            <h3>Configuración de Impuestos</h3>
            <label>
              Porcentaje de IVA
              <div class="iva-input">
                <input
                  v-if="ivaEditMode"
                  v-model.number="ivaDraft.porcentaje"
                  type="number"
                  min="0"
                  max="100"
                />
                <input
                  v-else
                  :value="Number(ivaForm.porcentaje || 0)"
                  type="text"
                  readonly
                />
                <span>%</span>
              </div>
            </label>

            <div class="iva-actions">
              <template v-if="ivaEditMode">
                <button class="icon-btn success" type="button" aria-label="Aceptar cambios de IVA" @click="submitIva">✓</button>
                <button class="icon-btn danger" type="button" aria-label="Descartar cambios de IVA" @click="cancelIvaEdit">✕</button>
              </template>
              <button
                v-else
                class="icon-btn"
                type="button"
                aria-label="Editar IVA"
                @click="startIvaEdit"
              >
                ✏️
              </button>
            </div>
          </div>
        </section>

        <section v-else class="iva-tab-panel">
          <div class="card iva-card services-pdf-card">
            <h3>PDF de servicios adicionales</h3>
            <p class="services-pdf-description">Este PDF se anexará automáticamente al documento de cotización al confirmar y descargar.</p>

            <p v-if="additionalServicesPdf.has_file" class="services-pdf-status">
              Archivo actual: <strong>{{ additionalServicesPdf.filename }}</strong>
            </p>
            <p v-else class="services-pdf-status">No hay archivo cargado actualmente.</p>

            <label class="services-pdf-label" for="additional-services-pdf">Seleccionar PDF</label>
            <input
              id="additional-services-pdf"
              class="services-pdf-input"
              type="file"
              accept="application/pdf,.pdf"
              @change="onAdditionalServicesPdfChange"
            />

            <div class="modal-actions services-pdf-actions">
              <button
                class="btn-primary"
                type="button"
                :disabled="isUploadingAdditionalPdf"
                @click="uploadAdditionalServicesPdf"
              >
                {{ isUploadingAdditionalPdf ? 'Subiendo...' : 'Subir PDF' }}
              </button>
            </div>
          </div>
        </section>
      </template>
    </main>

    <div v-if="userModal.open" class="modal-backdrop">
      <div class="modal">
        <h3>{{ userModal.mode === 'create' ? 'Crear usuario' : 'Editar usuario' }}</h3>
        <label>Nombre completo <input v-model="userForm.nombre" type="text" /></label>
        <label>Correo electrónico <input v-model="userForm.email" type="email" /></label>
        <p v-if="userModal.mode === 'create'" class="helper-text">
          Al crear el usuario se generará un código de validación automático y será enviado a su correo.
        </p>
        <label>
          Rol
          <select v-model="userForm.rol">
            <option value="SALES_USER">Usuario</option>
            <option value="ADMIN">Administrador</option>
          </select>
        </label>
        <div class="modal-actions">
          <button class="btn-link" type="button" @click="closeUserModal">Cancelar</button>
          <button class="btn-primary" type="button" @click="submitUser">Guardar</button>
        </div>
      </div>
    </div>

    <div v-if="planModal.open" class="modal-backdrop">
      <div class="modal price-modal">
        <h3 class="price-modal-title">{{ planForm.nombre || (planModal.type === 'plan' ? 'Nuevo plan' : 'Nueva prestación') }}</h3>

        <div class="price-modal-grid">
          <label class="price-modal-row">
            <span>Nombre</span>
            <input v-model="planForm.nombre" type="text" />
          </label>

          <template v-if="planModal.type === 'plan'">
            <label class="price-modal-row">
              <span>Conexiones</span>
              <input v-model.number="planForm.conexiones_incluidas" type="number" min="1" />
            </label>

            <p class="price-modal-subtitle">Precios</p>

            <label class="price-modal-row">
              <span>Valor plan mensual</span>
              <input v-model.number="planForm.valor_plan_mensual" type="number" min="0" />
            </label>
            <label class="price-modal-row">
              <span>Valor conexión extra</span>
              <input v-model.number="planForm.valor_conexion_adicional" type="number" min="0" />
            </label>
          </template>

          <template v-else>
            <label class="price-modal-row">
              <span>Valor unitario</span>
              <input v-model.number="planForm.valor_unitario" type="number" min="0" />
            </label>

            <label class="price-modal-row">
              <span>Tipo moneda</span>
              <select v-model="planForm.clp">
                <option :value="true">CLP</option>
                <option :value="false">UF</option>
              </select>
            </label>
          </template>

          <label class="price-modal-row">
            <span>Condiciones</span>
            <textarea v-model="planForm.condiciones" rows="2"></textarea>
          </label>

          <label v-if="planModal.type === 'plan'" class="price-modal-row">
            <span>Mensajes WhatsApp</span>
            <input v-model.number="planForm.mensajes_whatsapp" type="number" min="0" />
          </label>
        </div>

        <div class="price-modal-actions">
          <button class="icon-btn success" type="button" @click="submitPrice">✓</button>
          <button class="icon-btn danger" type="button" @click="closePriceModal">✕</button>
        </div>
      </div>
    </div>

    <div v-if="platformTrainingModal.open" class="modal-backdrop">
      <div class="modal">
        <h3>{{ platformTrainingModal.mode === 'create' ? 'Nueva relación de capacitación' : 'Editar relación de capacitación' }}</h3>
        <label>
          Conexiones desde
          <input v-model.number="platformTrainingForm.conexiones_desde" type="number" min="1" />
        </label>
        <label>
          Conexiones hasta (vacío = en adelante)
          <input v-model.number="platformTrainingForm.conexiones_hasta" type="number" min="1" />
        </label>
        <label>
          Horas de capacitación
          <input v-model.number="platformTrainingForm.horas_capacitacion" type="number" min="0" />
        </label>
        <div class="modal-actions">
          <button class="btn-link" type="button" @click="closePlatformTrainingModal">Cancelar</button>
          <button class="btn-primary" type="button" @click="submitPlatformTrainingRule">Guardar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page { min-height: 100vh; background: #f5f7fb; color: #1d2b3a; }
.topbar { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: #fff; border-bottom: 1px solid #dfe5ef; }
.topbar h2 { margin: 0; font-size: 24px; }
.topbar p { margin: 4px 0 0; font-size: 13px; color: #66798f; }
.topbar-user { display: flex; align-items: center; gap: 10px; }
.admin-user-pill {
  background: linear-gradient(135deg, rgba(26,163,255,0.08), rgba(2,22,66,0.04));
  padding: 8px 12px;
  border-radius: 20px;
  color: #0f2140;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 260px;
  border: 1px solid rgba(26,163,255,0.15);
  transition: all 0.2s ease;
}
.admin-user-pill:hover {
  background: linear-gradient(135deg, rgba(26,163,255,0.12), rgba(2,22,66,0.06));
  border-color: rgba(26,163,255,0.25);
}
.admin-user-icon {
  font-size: 16px;
  min-width: 16px;
}
.admin-user-name {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.admin-exit-btn {
  background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
  border: none;
  padding: 8px 14px;
  border-radius: 20px;
  color: #fff;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(255,107,107,0.2);
}
.admin-exit-btn:hover {
  background: linear-gradient(135deg, #ff5252, #dd4e63);
  box-shadow: 0 4px 12px rgba(255,107,107,0.3);
  transform: translateY(-1px);
}
.admin-exit-icon {
  width: 16px;
  height: 16px;
  object-fit: contain;
}

.content { padding: 20px 24px; }
.tab-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  margin: 0 auto 14px;
  padding: 6px;
  border-radius: 12px;
  background: #dce1e6;
  width: min(880px, 100%);
}
.tab {
  border: 1px solid transparent;
  background: transparent;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #61758e;
  font-size: 15px;
  font-weight: 500;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}
.tab-icon {
  color: #96a3b5;
  font-size: 20px;
  line-height: 1;
}
.tab span:last-child {
  white-space: nowrap;
}
.tab.active {
  background: #f8f8f9;
  color: #1f2329;
  border-color: #d4d8de;
}
.tab.active .tab-icon { color: #1f2329; }
.tab:not(.active):hover {
  background: rgba(255, 255, 255, 0.4);
  color: #506377;
}
.card { background: #fff; border: 1px solid #dfe5ef; border-radius: 12px; padding: 16px; }

.collapsible-header {
  gap: 10px;
}

.collapse-toggle {
  border: none;
  background: transparent;
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.collapse-toggle h3 {
  margin: 0;
}

.collapse-arrow {
  display: inline-flex;
  color: #4c5f74;
  font-size: 16px;
  transition: transform 0.2s ease;
}

.collapse-arrow.collapsed {
  transform: rotate(-90deg);
}
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-header h3 { margin: 0; }
.search { width: 100%; margin-bottom: 12px; padding: 10px; border: 1px solid #ced7e4; border-radius: 8px; }
.entity-list, .cards-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.entity-row { display: flex; justify-content: space-between; align-items: center; border: 1px solid #e1e6ef; border-radius: 10px; padding: 12px; }
.entity-row p { margin: 4px 0; color: #4d627d; }
.actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: nowrap;
}
.icon-btn {
  width: 38px;
  height: 38px;
  border: none;
  background: #d0d3d8;
  border-radius: 50%;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}
.icon-btn.danger { background: #f43f5e; color: #fff; }
.prices-grid { display: grid; grid-template-columns: 1fr; gap: 20px; }
.prices-section {
  display: grid;
  gap: 10px;
}
.prices-header { margin-bottom: 16px; }
.prices-cards-list {
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  grid-auto-rows: 1fr;
  align-items: stretch;
}
.price-card {
  border: 2px solid #56bdf1;
  border-radius: 14px;
  background: #fff;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  height: 100%;
}
.price-card h4 { margin: 0; text-align: center; font-size: 16px; color: #1f2d3d; }
.price-field {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  font-size: 12px;
}
.price-field span { color: #4b5e77; }
.price-field strong { color: #1a2430; font-weight: 700; }
.price-card small {
  margin: 0;
  min-height: 24px;
  color: #6f8197;
  font-size: 11px;
  border-radius: 8px;
  padding: 4px 8px;
  background: #f6f8fb;
}
.price-card .actions {
  justify-content: flex-end;
  margin-top: auto;
  padding-top: 4px;
}
.training-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.training-row {
  border: 1px solid #d7e2ef;
  border-radius: 10px;
  padding: 9px 10px;
  background: #fbfdff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.training-data {
  display: grid;
  gap: 2px;
}
.training-data strong {
  color: #243447;
  font-size: 13px;
}
.training-data span {
  color: #5d7188;
  font-size: 12px;
}
.iva-tab-panel {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 52px 0 18px;
}
.iva-card {
  width: min(92vw, 365px);
  border-radius: 26px;
  border: 1px solid #c5ccd6;
  background: #f9fafc;
  display: grid;
  gap: 18px;
  justify-items: center;
  padding: 44px 30px 24px;
}
.iva-card h3 {
  margin: 0;
  font-size: 28px;
  line-height: 1.12;
  text-align: center;
  color: #243449;
  font-weight: 700;
}
.iva-card label {
  display: grid;
  gap: 14px;
  justify-items: center;
  color: #3c4f67;
  font-weight: 600;
  font-size: 18px;
}
.iva-input { display: flex; gap: 10px; align-items: center; }
.iva-input input {
  width: 128px;
  height: 48px;
  border: 1px solid #cad1dc;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 20px;
  text-align: left;
  color: #3d4c5f;
  background: #fff;
}
.iva-input span {
  font-size: 24px;
  color: #73859c;
}
.iva-actions {
  min-height: 62px;
  width: 100%;
  display: flex;
  justify-content: center;
  gap: 28px;
}
.iva-actions .icon-btn {
  width: 54px;
  height: 54px;
  font-size: 30px;
}
.services-pdf-card {
  justify-items: stretch;
}
.services-pdf-card h3,
.services-pdf-description,
.services-pdf-status,
.services-pdf-label {
  text-align: left;
}
.services-pdf-description,
.services-pdf-status {
  margin: 0;
}
.services-pdf-input {
  width: 100%;
}
.services-pdf-actions {
  width: 100%;
  justify-content: flex-end;
  margin-top: 0;
}
.icon-btn.success { background: #34d058; color: #fff; }

.btn-primary { border: none; background: #0ea5e9; color: #fff; border-radius: 8px; padding: 9px 14px; cursor: pointer; }
.add-price-btn {
  border-radius: 999px;
  padding: 10px 18px;
  font-weight: 600;
  box-shadow: 0 6px 14px rgba(14, 165, 233, 0.25);
}
.btn-link { border: none; background: transparent; color: #1d2b3a; cursor: pointer; }
.feedback { margin: 0 0 10px; padding: 10px; border-radius: 8px; }
.feedback.success { background: #e8f8ef; color: #117c39; }
.feedback.error { background: #fdecec; color: #b3261e; }
.empty-state { color: #687b93; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(11, 18, 35, 0.55); display: flex; justify-content: center; align-items: center; z-index: 20; }
.modal { width: min(92vw, 460px); background: #fff; border-radius: 12px; padding: 16px; display: grid; gap: 10px; }
.modal h3 { margin: 0; }
.modal label { display: grid; gap: 6px; font-size: 14px; }
.modal input, .modal select, .modal textarea, .iva-card input { border: 1px solid #cad4e2; border-radius: 8px; padding: 9px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px; }

.price-modal {
  width: min(92vw, 760px);
  border: 4px solid #1ea6e7;
  border-radius: 44px;
  padding: 28px 44px 22px;
  gap: 20px;
}
.price-modal-title {
  margin: 0;
  text-align: center;
  font-size: 34px;
  line-height: 1.1;
  font-weight: 500;
}
.price-modal-grid {
  display: grid;
  gap: 14px;
}
.price-modal-subtitle {
  text-align: center;
  color: #919eae;
  font-size: 24px;
  margin: 0;
  line-height: 1;
}
.price-modal-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  align-items: center;
}
.price-modal-row span {
  font-size: 22px;
  color: #2b333f;
}
.price-modal-row input,
.price-modal-row select,
.price-modal-row textarea {
  border: 2px solid #a9adb3;
  border-radius: 14px;
  min-height: 44px;
  font-size: 18px;
  padding: 8px 18px;
}
.price-modal-row select {
  appearance: none;
  background-color: #fff;
  background-image: linear-gradient(45deg, transparent 50%, #5f6670 50%), linear-gradient(135deg, #5f6670 50%, transparent 50%);
  background-position: calc(100% - 24px) calc(50% - 4px), calc(100% - 16px) calc(50% - 4px);
  background-size: 8px 8px, 8px 8px;
  background-repeat: no-repeat;
  padding-right: 44px;
}
.price-modal-row textarea {
  min-height: 68px;
  resize: none;
}
.price-modal-actions {
  display: flex;
  justify-content: center;
  gap: 36px;
  margin-top: 2px;
}
.price-modal .icon-btn {
  width: 58px;
  height: 58px;
  font-size: 32px;
  color: #fff;
}
.price-modal .icon-btn.success { background: #35d34f; }

.helper-text {
  margin: -2px 0 4px;
  font-size: 14px;
  color: #4c5a67;
}

.dynamic-attribute-row {
  display: grid;
  grid-template-columns: 1.2fr .9fr 1.2fr auto;
  gap: 10px;
  align-items: center;
}
.dynamic-attribute-row .icon-btn {
  width: 42px;
  height: 42px;
}
@media (max-width: 960px) {
}
@media (max-width: 680px) {
  .dynamic-attribute-row { grid-template-columns: 1fr; }
}

@media (max-width: 1200px) {
  .price-modal { width: min(92vw, 620px); padding: 24px 28px 20px; }
  .price-modal-title { font-size: 30px; }
  .price-modal-subtitle { font-size: 22px; }
  .price-modal-row span { font-size: 20px; }
  .price-modal-row input,
  .price-modal-row select,
  .price-modal-row textarea { font-size: 17px; min-height: 42px; }
}

@media (max-width: 960px) {
  .price-modal-title { font-size: 28px; }
  .price-modal-subtitle { font-size: 20px; }
  .price-modal-row span { font-size: 18px; }
  .price-modal-row input,
  .price-modal-row select,
  .price-modal-row textarea { font-size: 16px; }
  .iva-card h3 { font-size: 24px; }
  .iva-card label { font-size: 16px; }
}

@media (max-width: 680px) {
  .tab-row {
    padding: 6px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .tab { font-size: 14px; padding: 8px 6px; gap: 6px; }
  .tab-icon { font-size: 18px; }
  .price-modal { padding: 18px; border-radius: 26px; }
  .price-modal-row { grid-template-columns: 1fr; gap: 6px; }
  .price-modal-actions { gap: 20px; }
  .price-modal .icon-btn { width: 58px; height: 58px; font-size: 30px; }
  .iva-tab-panel { padding-top: 24px; }
  .iva-card { padding: 30px 16px 20px; gap: 14px; }
  .iva-card h3 { font-size: 22px; }
  .iva-card label { font-size: 17px; gap: 8px; }
  .iva-input input { width: 96px; height: 40px; font-size: 20px; }
  .iva-input span { font-size: 22px; }
  .iva-actions { gap: 14px; min-height: 46px; }
  .iva-actions .icon-btn { width: 42px; height: 42px; font-size: 24px; }
}
</style>
