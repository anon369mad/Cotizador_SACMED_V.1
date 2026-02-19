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
const ivaConfig = ref([])

const userSearch = ref('')

const userModal = ref({ open: false, mode: 'create', id: null })
const userForm = reactive({
  nombre: '',
  email: '',
  password: '',
  confirmPassword: '',
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
  dynamic_attributes: []
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


function createEmptyDynamicAttribute() {
  return { key: '', value: '', type: 'text' }
}

function normalizeAdditionalAttributes(attributes) {
  if (!attributes || typeof attributes !== 'object' || Array.isArray(attributes)) return []

  return Object.entries(attributes).map(([key, value]) => {
    let type = 'text'
    let normalizedValue = value

    if (typeof value === 'number') {
      type = 'number'
      normalizedValue = Number(value)
    } else if (typeof value === 'boolean') {
      type = 'boolean'
      normalizedValue = value ? 'true' : 'false'
    } else if (value == null) {
      normalizedValue = ''
    } else {
      normalizedValue = String(value)
    }

    return { key, value: normalizedValue, type }
  })
}

function resetDynamicAttributes(attributes = null) {
  const normalized = normalizeAdditionalAttributes(attributes)
  planForm.dynamic_attributes = normalized.length ? normalized : [createEmptyDynamicAttribute()]
}

function addDynamicAttribute() {
  planForm.dynamic_attributes.push(createEmptyDynamicAttribute())
}

function removeDynamicAttribute(index) {
  planForm.dynamic_attributes.splice(index, 1)
  if (!planForm.dynamic_attributes.length) {
    addDynamicAttribute()
  }
}

function buildAdditionalAttributesPayload() {
  const payload = {}
  const names = new Set()

  for (const item of planForm.dynamic_attributes) {
    const key = String(item.key || '').trim()
    const rawValue = item.value

    if (!key) {
      if (String(rawValue || '').trim()) {
        throw new Error('Cada atributo adicional debe tener un nombre')
      }
      continue
    }

    if (names.has(key)) {
      throw new Error(`El atributo adicional "${key}" está repetido`)
    }
    names.add(key)

    if (item.type === 'number') {
      if (rawValue === '' || rawValue === null || Number.isNaN(Number(rawValue))) {
        throw new Error(`El atributo "${key}" debe tener un número válido`)
      }
      payload[key] = Number(rawValue)
    } else if (item.type === 'boolean') {
      payload[key] = rawValue === 'true' || rawValue === true
    } else {
      payload[key] = rawValue == null ? '' : String(rawValue)
    }
  }

  return payload
}

function buildPlanPayloadFromEntry(entry, attributes) {
  return {
    nombre: String(entry?.nombre || '').trim(),
    conexiones_incluidas: Number(entry?.conexiones_incluidas || 0),
    valor_plan_mensual: Number(entry?.valor_plan_mensual || 0),
    valor_conexion_adicional: Number(entry?.valor_conexion_adicional || 0),
    condiciones: entry?.condiciones || '',
    activo: entry?.activo !== false,
    atributos_adicionales: attributes
  }
}

function buildServicePayloadFromEntry(entry, attributes) {
  return {
    nombre: String(entry?.nombre || '').trim(),
    valor_unitario: Number(entry?.valor_unitario || 0),
    condiciones: entry?.condiciones || '',
    activo: entry?.activo !== false,
    clp: entry?.clp !== false,
    atributos_adicionales: attributes
  }
}

async function syncAdditionalAttributeKeys(type, sourceAttributes) {
  const expectedKeys = Object.keys(sourceAttributes || {})
  if (!expectedKeys.length) return 0

  const source = type === 'plan' ? plans.value : services.value
  let updatedCount = 0

  for (const entry of source) {
    const currentAttributes = {
      ...(entry?.atributos_adicionales && typeof entry.atributos_adicionales === 'object'
        ? entry.atributos_adicionales
        : {})
    }

    let changed = false
    for (const key of expectedKeys) {
      if (Object.prototype.hasOwnProperty.call(currentAttributes, key)) continue
      currentAttributes[key] = ''
      changed = true
    }

    if (!changed) continue

    const endpoint = type === 'plan' ? `/planes/${entry.id_plan}` : `/prestaciones/${entry.id_prestacion}`
    const payload = type === 'plan'
      ? buildPlanPayloadFromEntry(entry, currentAttributes)
      : buildServicePayloadFromEntry(entry, currentAttributes)

    await request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(payload)
    })
    updatedCount += 1
  }

  return updatedCount
}

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
  const [allPlans, allServices] = await Promise.all([
    request('/planes'),
    request('/prestaciones')
  ])
  plans.value = Array.isArray(allPlans) ? allPlans : []
  services.value = Array.isArray(allServices) ? allServices : []
}

async function loadIva() {
  const allIva = await request('/iva')
  ivaConfig.value = Array.isArray(allIva) ? allIva : []

  if (ivaConfig.value.length) {
    const current = ivaConfig.value[0]
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
    await Promise.all([loadUsers(), loadPrices(), loadIva()])
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
    password: '',
    confirmPassword: '',
    rol: 'SALES_USER',
    activo: true
  })
}

function openEditUser(user) {
  userModal.value = { open: true, mode: 'edit', id: user.id_usuario }
  Object.assign(userForm, {
    nombre: user.nombre || '',
    email: user.email || '',
    password: '',
    confirmPassword: '',
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

  if (userModal.value.mode === 'create' && userForm.password.trim().length < 6) {
    showFeedback('La contraseña debe tener al menos 6 caracteres', 'error')
    return
  }

  if (userForm.password && userForm.password !== userForm.confirmPassword) {
    showFeedback('La confirmación de contraseña no coincide', 'error')
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
        body: JSON.stringify({ ...payload, password: userForm.password.trim() })
      })
      showFeedback('Usuario creado correctamente')
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
    clp: true
  })
  resetDynamicAttributes()
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
    clp: entry.clp !== false
  })
  resetDynamicAttributes(entry.atributos_adicionales)
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
    const additionalAttributes = buildAdditionalAttributesPayload()

    if (planModal.value.type === 'plan') {
      const payload = {
        nombre: planForm.nombre.trim(),
        conexiones_incluidas: Number(planForm.conexiones_incluidas || 0),
        valor_plan_mensual: Number(planForm.valor_plan_mensual || 0),
        valor_conexion_adicional: Number(planForm.valor_conexion_adicional || 0),
        condiciones: planForm.condiciones,
        activo: planForm.activo,
        atributos_adicionales: additionalAttributes
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
        clp: planForm.clp,
        atributos_adicionales: additionalAttributes
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

    const updatedCount = await syncAdditionalAttributeKeys(planModal.value.type, additionalAttributes)
    if (updatedCount > 0) {
      await loadPrices()
    }

    const baseMessage = planModal.value.mode === 'create' ? 'Registro creado correctamente' : 'Registro actualizado correctamente'
    const syncMessage = updatedCount > 0
      ? ` Se propagaron ${updatedCount} registro${updatedCount === 1 ? '' : 's'} para mantener los atributos alineados.`
      : ''
    showFeedback(`${baseMessage}.${syncMessage}`)
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

async function submitIva() {
  resetFeedback()
  try {
    const payload = {
      nombre: ivaDraft.nombre.trim() || 'IVA',
      porcentaje: Number(ivaDraft.porcentaje || 0),
      activo: ivaDraft.activo
    }

    if (ivaForm.id_iva) {
      await request(`/iva/${ivaForm.id_iva}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      })
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
        <span>{{ userName }}</span>
        <span class="badge">Admin</span>
        <button class="btn-link" type="button" @click="logout">Salir</button>
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
        </div>

        <p v-if="feedback" class="feedback" :class="feedbackType">{{ feedback }}</p>
        <div v-if="isLoading" class="card empty-state">Cargando panel administrativo...</div>

        <section v-else-if="activeTab === 'usuarios'" class="card">
          <div class="section-header">
            <h3>Gestión de usuarios</h3>
            <button class="btn-primary" type="button" @click="openCreateUser">+ Nuevo usuario</button>
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
            <div>
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
                  <small>{{ plan.condiciones || 'Sin condiciones' }}</small>
                  <ul v-if="plan.atributos_adicionales && Object.keys(plan.atributos_adicionales).length" class="dynamic-attributes-list">
                    <li v-for="(value, key) in plan.atributos_adicionales" :key="`plan-${plan.id_plan}-${key}`">{{ key }}: {{ value }}</li>
                  </ul>
                  <div class="actions">
                    <button class="icon-btn" type="button" @click="openEditPrice('plan', plan)">✏️</button>
                    <button class="icon-btn danger" type="button" @click="deletePrice('plan', plan)">🗑️</button>
                  </div>
                </li>
              </ul>
            </div>

            <div>
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
                  <ul v-if="service.atributos_adicionales && Object.keys(service.atributos_adicionales).length" class="dynamic-attributes-list">
                    <li v-for="(value, key) in service.atributos_adicionales" :key="`service-${service.id_prestacion}-${key}`">{{ key }}: {{ value }}</li>
                  </ul>
                  <div class="actions">
                    <button class="icon-btn" type="button" @click="openEditPrice('servicio', service)">✏️</button>
                    <button class="icon-btn danger" type="button" @click="deletePrice('servicio', service)">🗑️</button>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>

        <section v-else class="iva-tab-panel">
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
      </template>
    </main>

    <div v-if="userModal.open" class="modal-backdrop">
      <div class="modal">
        <h3>{{ userModal.mode === 'create' ? 'Crear usuario' : 'Editar usuario' }}</h3>
        <label>Nombre completo <input v-model="userForm.nombre" type="text" /></label>
        <label>Correo electrónico <input v-model="userForm.email" type="email" /></label>
        <label v-if="userModal.mode === 'create'">Contraseña <input v-model="userForm.password" type="password" /></label>
        <label v-if="userModal.mode === 'create'">Confirmar contraseña <input v-model="userForm.confirmPassword" type="password" /></label>
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

          <div class="dynamic-attributes-editor">
            <div class="dynamic-attributes-header">
              <span>Atributos adicionales</span>
              <button class="btn-primary" type="button" @click="addDynamicAttribute">+ Agregar atributo</button>
            </div>

            <div
              v-for="(attribute, index) in planForm.dynamic_attributes"
              :key="`attr-${index}`"
              class="dynamic-attribute-row"
            >
              <input v-model="attribute.key" type="text" placeholder="Nombre" />
              <select v-model="attribute.type">
                <option value="text">Texto</option>
                <option value="number">Número</option>
                <option value="boolean">Booleano</option>
              </select>
              <input
                v-if="attribute.type !== 'boolean'"
                v-model="attribute.value"
                :type="attribute.type === 'number' ? 'number' : 'text'"
                placeholder="Valor"
              />
              <select v-else v-model="attribute.value">
                <option value="true">Sí</option>
                <option value="false">No</option>
              </select>
              <button class="icon-btn danger" type="button" @click="removeDynamicAttribute(index)">−</button>
            </div>
          </div>
        </div>

        <div class="price-modal-actions">
          <button class="icon-btn success" type="button" @click="submitPrice">✓</button>
          <button class="icon-btn danger" type="button" @click="closePriceModal">✕</button>
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
.badge { background: #0ea5e9; color: #fff; border-radius: 999px; padding: 2px 10px; font-size: 12px; }

.content { padding: 20px 24px; }
.tab-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 14px;
  padding: 8px;
  border-radius: 14px;
  background: #dce1e6;
}
.tab {
  border: 1px solid transparent;
  background: transparent;
  padding: 14px 16px;
  border-radius: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #61758e;
  font-size: 20px;
  font-weight: 500;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}
.tab-icon {
  color: #96a3b5;
  font-size: 33px;
  line-height: 1;
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
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-header h3 { margin: 0; }
.search { width: 100%; margin-bottom: 12px; padding: 10px; border: 1px solid #ced7e4; border-radius: 8px; }
.entity-list, .cards-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.entity-row { display: flex; justify-content: space-between; align-items: center; border: 1px solid #e1e6ef; border-radius: 10px; padding: 12px; }
.entity-row p { margin: 4px 0; color: #4d627d; }
.actions { display: flex; gap: 8px; }
.icon-btn {
  width: 36px;
  height: 36px;
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
.prices-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.prices-header { margin-bottom: 16px; }
.prices-cards-list {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;
}
.price-card {
  border: 3px solid #56bdf1;
  border-radius: 20px;
  background: #fff;
  padding: 12px 14px;
  display: grid;
  gap: 7px;
  align-content: start;
}
.price-card h4 { margin: 0; text-align: center; font-size: 20px; color: #1f2d3d; }
.price-field {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  font-size: 13px;
}
.price-field span { color: #4b5e77; }
.price-field strong { color: #1a2430; font-weight: 700; }
.price-card small {
  margin: 0;
  min-height: 28px;
  color: #6f8197;
  font-size: 12px;
  border-radius: 8px;
  padding: 4px 8px;
  background: #f6f8fb;
}
.price-card .actions {
  justify-content: space-between;
  margin-top: 4px;
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
  font-size: 34px;
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
  font-size: 23px;
}
.iva-input { display: flex; gap: 10px; align-items: center; }
.iva-input input {
  width: 128px;
  height: 48px;
  border: 1px solid #cad1dc;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 24px;
  text-align: left;
  color: #3d4c5f;
  background: #fff;
}
.iva-input span {
  font-size: 29px;
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
  font-size: 46px;
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
  font-size: 34px;
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
  font-size: 40px;
  color: #2b333f;
}
.price-modal-row input,
.price-modal-row select,
.price-modal-row textarea {
  border: 2px solid #a9adb3;
  border-radius: 24px;
  min-height: 56px;
  font-size: 34px;
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
  min-height: 82px;
  resize: none;
}
.price-modal-actions {
  display: flex;
  justify-content: center;
  gap: 78px;
  margin-top: 2px;
}
.price-modal .icon-btn {
  width: 82px;
  height: 82px;
  font-size: 48px;
  color: #fff;
}
.price-modal .icon-btn.success { background: #35d34f; }

.dynamic-attributes-list {
  margin: 0;
  padding-left: 18px;
  color: #47586d;
  font-size: 12px;
}
.dynamic-attributes-editor {
  display: grid;
  gap: 10px;
  border: 1px solid #d8e1eb;
  border-radius: 16px;
  padding: 12px;
}
.dynamic-attributes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.dynamic-attributes-header span {
  font-size: 28px;
  color: #2b333f;
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
  .dynamic-attributes-header span { font-size: 20px; }
}
@media (max-width: 680px) {
  .dynamic-attribute-row { grid-template-columns: 1fr; }
}

@media (max-width: 1200px) {
  .price-modal { width: min(92vw, 620px); padding: 24px 28px 20px; }
  .price-modal-title { font-size: 38px; }
  .price-modal-subtitle { font-size: 28px; }
  .price-modal-row span { font-size: 30px; }
  .price-modal-row input,
  .price-modal-row select,
  .price-modal-row textarea { font-size: 24px; min-height: 48px; }
}

@media (max-width: 960px) {
  .prices-grid { grid-template-columns: 1fr; }
  .price-modal-title { font-size: 32px; }
  .price-modal-subtitle { font-size: 24px; }
  .price-modal-row span { font-size: 22px; }
  .price-modal-row input,
  .price-modal-row select,
  .price-modal-row textarea { font-size: 18px; }
  .iva-card h3 { font-size: 28px; }
  .iva-card label { font-size: 20px; }
}

@media (max-width: 680px) {
  .tab-row { padding: 6px; }
  .tab { font-size: 16px; padding: 10px 8px; gap: 6px; }
  .tab-icon { font-size: 22px; }
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
