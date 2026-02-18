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
  clp: true
})

const ivaForm = reactive({
  id_iva: null,
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
  }
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
        activo: planForm.activo
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

    showFeedback(planModal.value.mode === 'create' ? 'Registro creado correctamente' : 'Registro actualizado correctamente')
    await loadPrices()
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
      nombre: ivaForm.nombre.trim() || 'IVA',
      porcentaje: Number(ivaForm.porcentaje || 0),
      activo: ivaForm.activo
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
        <div class="tab-row">
          <button class="tab" :class="{ active: activeTab === 'usuarios' }" @click="activeTab = 'usuarios'">Usuarios</button>
          <button class="tab" :class="{ active: activeTab === 'precios' }" @click="activeTab = 'precios'">Precios</button>
          <button class="tab" :class="{ active: activeTab === 'iva' }" @click="activeTab = 'iva'">% IVA</button>
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
              <div class="section-header">
                <h3>Planes</h3>
                <button class="btn-primary" type="button" @click="openCreatePrice('plan')">+ Nuevo plan</button>
              </div>
              <ul class="cards-list">
                <li v-for="plan in plans" :key="plan.id_plan" class="price-card">
                  <h4>{{ plan.nombre }}</h4>
                  <p>Conexiones: {{ plan.conexiones_incluidas }}</p>
                  <p>Mensual: {{ Number(plan.valor_plan_mensual).toLocaleString('es-CL') }}</p>
                  <p>Conexión extra: {{ Number(plan.valor_conexion_adicional).toLocaleString('es-CL') }}</p>
                  <small>{{ plan.condiciones || 'Sin condiciones' }}</small>
                  <div class="actions">
                    <button class="icon-btn" type="button" @click="openEditPrice('plan', plan)">✏️</button>
                    <button class="icon-btn danger" type="button" @click="deletePrice('plan', plan)">🗑️</button>
                  </div>
                </li>
              </ul>
            </div>

            <div>
              <div class="section-header">
                <h3>Prestaciones</h3>
                <button class="btn-primary" type="button" @click="openCreatePrice('servicio')">+ Nuevo servicio</button>
              </div>
              <ul class="cards-list">
                <li v-for="service in services" :key="service.id_prestacion" class="price-card">
                  <h4>{{ service.nombre }}</h4>
                  <p>Valor unitario: {{ Number(service.valor_unitario || 0).toLocaleString('es-CL') }}</p>
                  <small>{{ service.condiciones || 'Sin condiciones' }}</small>
                  <div class="actions">
                    <button class="icon-btn" type="button" @click="openEditPrice('servicio', service)">✏️</button>
                    <button class="icon-btn danger" type="button" @click="deletePrice('servicio', service)">🗑️</button>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>

        <section v-else class="card iva-card">
          <h3>Configuración de IVA</h3>
          <label>
            Nombre
            <input v-model="ivaForm.nombre" type="text" />
          </label>
          <label>
            Porcentaje de IVA
            <div class="iva-input">
              <input v-model.number="ivaForm.porcentaje" type="number" min="0" max="100" />
              <span>%</span>
            </div>
          </label>
          <button class="btn-primary" type="button" @click="submitIva">Guardar IVA</button>
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
      <div class="modal">
        <h3>{{ planModal.mode === 'create' ? 'Crear registro' : 'Editar registro' }}</h3>
        <label>Nombre <input v-model="planForm.nombre" type="text" /></label>

        <template v-if="planModal.type === 'plan'">
          <label>Conexiones incluidas <input v-model.number="planForm.conexiones_incluidas" type="number" min="1" /></label>
          <label>Valor plan mensual <input v-model.number="planForm.valor_plan_mensual" type="number" min="0" /></label>
          <label>Valor conexión adicional <input v-model.number="planForm.valor_conexion_adicional" type="number" min="0" /></label>
        </template>

        <label v-else>Valor unitario <input v-model.number="planForm.valor_unitario" type="number" min="0" /></label>
        <label>Condiciones <textarea v-model="planForm.condiciones" rows="3"></textarea></label>

        <div class="modal-actions">
          <button class="btn-link" type="button" @click="closePriceModal">Cancelar</button>
          <button class="btn-primary" type="button" @click="submitPrice">Guardar</button>
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
.tab-row { display: flex; gap: 8px; margin-bottom: 14px; }
.tab { border: 1px solid #d5dbe7; background: #fff; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
.tab.active { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }
.card { background: #fff; border: 1px solid #dfe5ef; border-radius: 12px; padding: 16px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-header h3 { margin: 0; }
.search { width: 100%; margin-bottom: 12px; padding: 10px; border: 1px solid #ced7e4; border-radius: 8px; }
.entity-list, .cards-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.entity-row { display: flex; justify-content: space-between; align-items: center; border: 1px solid #e1e6ef; border-radius: 10px; padding: 12px; }
.entity-row p { margin: 4px 0; color: #4d627d; }
.actions { display: flex; gap: 8px; }
.icon-btn { border: 1px solid #d5dbe7; background: #fff; border-radius: 8px; cursor: pointer; padding: 6px 10px; }
.icon-btn.danger { border-color: #f4b4b4; color: #d11a2a; }
.prices-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.price-card { border: 1px solid #dce4f0; border-radius: 10px; padding: 12px; display: grid; gap: 6px; }
.price-card h4 { margin: 0; }
.price-card p, .price-card small { margin: 0; }
.iva-card { max-width: 420px; display: grid; gap: 10px; }
.iva-card label { display: grid; gap: 6px; }
.iva-input { display: flex; gap: 8px; align-items: center; }

.btn-primary { border: none; background: #0ea5e9; color: #fff; border-radius: 8px; padding: 9px 14px; cursor: pointer; }
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

@media (max-width: 960px) {
  .prices-grid { grid-template-columns: 1fr; }
}
</style>
