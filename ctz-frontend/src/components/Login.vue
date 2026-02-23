<template>
  <div class="login-container">
    <Transition name="toast-fade">
      <div v-if="toast.visible" class="toast" :class="`toast--${toast.type}`" role="status" aria-live="polite">
        {{ toast.message }}
      </div>
    </Transition>

    <div class="login-card">
      <h1 class="title">Sistema de Cotizaciones</h1>
      <p class="subtitle">Ingresa tus credenciales para continuar</p>

      <form @submit.prevent="login" novalidate>
        <div class="form-group">
          <label for="email">Correo Electrónico</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="tu@sacmed.cl"
            required
            @input="clearFieldError('email')"
          />
          <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
        </div>

        <div class="form-group">
          <label for="password">Contraseña</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Ingresa tu contraseña"
            required
            @input="clearFieldError('password')"
          />
          <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
        </div>

        <button type="button" class="btn-link" @click="openRecoveryModal">
          ¿Olvidaste tu contraseña?
        </button>

        <button type="button" class="btn-link" @click="openFirstAccessModal">
          ¿Tienes código de primer acceso?
        </button>

        <p v-if="formError" class="form-error">{{ formError }}</p>
        <button class="btn-login" type="submit" :disabled="loading">
          {{ loading ? 'Ingresando...' : 'Iniciar Sesión' }}
        </button>
      </form>
    </div>

    <div v-if="showRecovery" class="modal-overlay" @click.self="closeRecoveryModal">
      <div class="modal-card">
        <div class="modal-header">
          <p class="recovery-title">Recuperar contraseña</p>
          <button type="button" class="modal-close" @click="closeRecoveryModal">×</button>
        </div>

        <div class="form-group">
          <label for="recovery-email">Correo de recuperación</label>
          <input
            id="recovery-email"
            v-model="recoveryEmail"
            type="email"
            placeholder="tu@sacmed.cl"
          />
        </div>

        <button class="btn-secondary" type="button" :disabled="recoveryLoading" @click="requestRecoveryToken">
          {{ recoveryLoading ? 'Generando token...' : 'Generar token' }}
        </button>

        <div class="form-group">
          <label for="reset-token">Token</label>
          <input id="reset-token" v-model="resetToken" type="text" placeholder="Pega aquí tu token" />
        </div>

        <div class="form-group">
          <label for="new-password">Nueva contraseña</label>
          <input
            id="new-password"
            v-model="newPassword"
            type="password"
            placeholder="Mínimo 6 caracteres"
          />
        </div>

        <button class="btn-secondary" type="button" :disabled="resetLoading" @click="resetPassword">
          {{ resetLoading ? 'Actualizando...' : 'Actualizar contraseña' }}
        </button>

        <p v-if="recoveryMessage" class="success-message">{{ recoveryMessage }}</p>
        <p v-if="recoveryError" class="form-error">{{ recoveryError }}</p>
      </div>
    </div>

    <div v-if="showFirstAccess" class="modal-overlay" @click.self="closeFirstAccessModal">
      <div class="modal-card">
        <div class="modal-header">
          <p class="recovery-title">Primer acceso</p>
          <button type="button" class="modal-close" @click="closeFirstAccessModal">×</button>
        </div>

        <p class="subtitle-small">
          Ingresa el código de validación enviado a tu correo y crea tu contraseña definitiva.
        </p>

        <div class="form-group">
          <label for="first-access-email">Correo</label>
          <input id="first-access-email" v-model="firstAccessEmail" type="email" placeholder="tu@sacmed.cl" />
        </div>

        <div class="form-group">
          <label for="first-access-code">Código de validación</label>
          <input id="first-access-code" v-model="firstAccessCode" type="text" placeholder="Código de 6 dígitos" />
        </div>

        <button class="btn-secondary" type="button" :disabled="firstAccessValidationLoading" @click="validateFirstAccessCode">
          {{ firstAccessValidationLoading ? 'Validando...' : 'Validar código' }}
        </button>

        <div class="form-group">
          <label for="first-access-password">Nueva contraseña</label>
          <input id="first-access-password" v-model="firstAccessPassword" type="password" placeholder="Mínimo 6 caracteres" />
        </div>

        <div class="form-group">
          <label for="first-access-password-confirm">Confirmar contraseña</label>
          <input id="first-access-password-confirm" v-model="firstAccessPasswordConfirm" type="password" placeholder="Repite tu contraseña" />
        </div>

        <button class="btn-secondary" type="button" :disabled="firstAccessSetPasswordLoading" @click="setFirstAccessPassword">
          {{ firstAccessSetPasswordLoading ? 'Guardando...' : 'Crear contraseña' }}
        </button>

        <p v-if="firstAccessMessage" class="success-message">{{ firstAccessMessage }}</p>
        <p v-if="firstAccessError" class="form-error">{{ firstAccessError }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    return {
      apiBaseUrl,
      email: '',
      password: '',
      errors: {},
      formError: '',
      loading: false,
      showFirstAccess: false,
      firstAccessEmail: '',
      firstAccessCode: '',
      firstAccessPassword: '',
      firstAccessPasswordConfirm: '',
      firstAccessValidationLoading: false,
      firstAccessSetPasswordLoading: false,
      firstAccessError: '',
      firstAccessMessage: '',
      showRecovery: false,
      recoveryEmail: '',
      resetToken: '',
      newPassword: '',
      recoveryLoading: false,
      resetLoading: false,
      recoveryError: '',
      recoveryMessage: '',
      toast: {
        visible: false,
        message: '',
        type: 'success'
      },
      toastTimeout: null
    }
  },
  beforeUnmount() {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout)
    }
  },
  methods: {
    showToast(message, type = 'success') {
      if (this.toastTimeout) {
        clearTimeout(this.toastTimeout)
      }

      this.toast = {
        visible: true,
        message,
        type
      }

      this.toastTimeout = setTimeout(() => {
        this.toast.visible = false
      }, 3200)
    },
    clearFieldError(field) {
      if (this.errors[field]) {
        this.errors = { ...this.errors, [field]: '' }
      }
    },
    openRecoveryModal() {
      this.showRecovery = true
      this.showFirstAccess = false
      this.recoveryError = ''
      this.recoveryMessage = ''
    },
    closeRecoveryModal() {
      this.showRecovery = false
    },
    openFirstAccessModal() {
      this.showFirstAccess = true
      this.showRecovery = false
      this.firstAccessError = ''
      this.firstAccessMessage = ''
    },
    closeFirstAccessModal() {
      this.showFirstAccess = false
    },
    validateForm() {
      const errors = {}
      const emailValue = this.email.trim()
      const passwordValue = this.password.trim()

      if (!emailValue) {
        errors.email = 'El correo es obligatorio.'
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailValue)) {
        errors.email = 'Ingresa un correo válido.'
      }

      if (!passwordValue) {
        errors.password = 'La contraseña es obligatoria.'
      } else if (passwordValue.length < 6) {
        errors.password = 'La contraseña debe tener al menos 6 caracteres.'
      }

      this.errors = errors
      return Object.keys(errors).length === 0
    },
    async requestRecoveryToken() {
      this.recoveryError = ''
      this.recoveryMessage = ''

      if (!this.recoveryEmail.trim()) {
        this.recoveryError = 'Debes ingresar un correo para recuperar la contraseña.'
        return
      }

      this.recoveryLoading = true
      try {
        const res = await fetch(`${this.apiBaseUrl}/password-recovery`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email: this.recoveryEmail.trim() })
        })

        const data = await res.json()

        if (!res.ok) {
          this.recoveryError = data?.detail || 'No fue posible generar el token de recuperación.'
          return
        }

        this.recoveryMessage = data.message
        this.showToast(data.message, 'success')
      } catch (error) {
        this.recoveryError = 'No fue posible conectar con el servicio de recuperación.'
      } finally {
        this.recoveryLoading = false
      }
    },
    async resetPassword() {
      this.recoveryError = ''
      this.recoveryMessage = ''

      if (!this.resetToken.trim()) {
        this.recoveryError = 'Debes ingresar el token de recuperación.'
        return
      }

      if (this.newPassword.trim().length < 6) {
        this.recoveryError = 'La nueva contraseña debe tener al menos 6 caracteres.'
        return
      }

      this.resetLoading = true
      try {
        const res = await fetch(`${this.apiBaseUrl}/password-reset`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            token: this.resetToken.trim(),
            new_password: this.newPassword.trim()
          })
        })

        const data = await res.json()

        if (!res.ok) {
          this.recoveryError = data?.detail || 'No fue posible actualizar la contraseña.'
          return
        }

        this.recoveryMessage = data.message
        this.password = ''
        this.showToast(data.message, 'success')
      } catch (error) {
        this.recoveryError = 'No fue posible conectar con el servicio de recuperación.'
      } finally {
        this.resetLoading = false
      }
    },
    async validateFirstAccessCode() {
      this.firstAccessError = ''
      this.firstAccessMessage = ''

      if (!this.firstAccessEmail.trim() || !this.firstAccessCode.trim()) {
        this.firstAccessError = 'Debes ingresar correo y código de validación.'
        return
      }

      this.firstAccessValidationLoading = true
      try {
        const res = await fetch(`${this.apiBaseUrl}/first-access/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: this.firstAccessEmail.trim(),
            access_code: this.firstAccessCode.trim()
          })
        })

        const data = await res.json()
        if (!res.ok) {
          this.firstAccessError = data?.detail || 'No se pudo validar el código de primer acceso.'
          return
        }

        this.firstAccessMessage = data.message
        this.showToast(data.message, 'success')
      } catch (error) {
        this.firstAccessError = 'No fue posible conectar con el servicio de primer acceso.'
      } finally {
        this.firstAccessValidationLoading = false
      }
    },
    async setFirstAccessPassword() {
      this.firstAccessError = ''
      this.firstAccessMessage = ''

      if (!this.firstAccessEmail.trim() || !this.firstAccessCode.trim()) {
        this.firstAccessError = 'Debes ingresar correo y código de validación.'
        return
      }

      if (this.firstAccessPassword.trim().length < 6) {
        this.firstAccessError = 'La contraseña debe tener al menos 6 caracteres.'
        return
      }

      if (this.firstAccessPassword.trim() !== this.firstAccessPasswordConfirm.trim()) {
        this.firstAccessError = 'Las contraseñas no coinciden.'
        return
      }

      this.firstAccessSetPasswordLoading = true
      try {
        const res = await fetch(`${this.apiBaseUrl}/first-access/set-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: this.firstAccessEmail.trim(),
            access_code: this.firstAccessCode.trim(),
            new_password: this.firstAccessPassword.trim()
          })
        })

        const data = await res.json()
        if (!res.ok) {
          this.firstAccessError = data?.detail || 'No se pudo crear la contraseña de primer acceso.'
          return
        }

        this.firstAccessMessage = data.message
        this.password = ''
        this.showToast(data.message, 'success')
      } catch (error) {
        this.firstAccessError = 'No fue posible conectar con el servicio de primer acceso.'
      } finally {
        this.firstAccessSetPasswordLoading = false
      }
    },
    async login() {
      this.formError = ''

      if (!this.validateForm()) {
        return
      }

      this.loading = true

      try {
        const res = await fetch(`${this.apiBaseUrl}/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: this.email.trim(),
            password: this.password.trim()
          })
        })

        if (!res.ok) {
          if (res.status === 401) {
            const trimmedPassword = this.password.trim()

            if (/^\d{6}$/.test(trimmedPassword)) {
              this.formError = 'Ese código corresponde al primer acceso. Debes usar "¿Tienes código de primer acceso?" para crear tu contraseña.'
              this.showToast('Usa el flujo de primer acceso para validar tu código y crear contraseña.', 'warning')
              this.showFirstAccess = true
              this.showRecovery = false
              this.firstAccessEmail = this.email.trim()
              this.firstAccessCode = trimmedPassword
              return
            }

            this.formError = 'Credenciales inválidas.'
            return
          }

          if (res.status === 403) {
            const payload = await res.json().catch(() => null)
            this.formError = payload?.detail || 'Debes completar el flujo de primer acceso.'
            this.showFirstAccess = true
            this.showRecovery = false
            this.firstAccessEmail = this.email.trim()
            return
          }

          throw new Error('No se pudo validar el usuario.')
        }

        const usuario = await res.json()

        localStorage.setItem('cotizador_user', JSON.stringify(usuario))
        this.$emit('login-ok', usuario)
      } catch (error) {
        this.formError = 'No pudimos iniciar sesión. Intenta nuevamente.'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.login-card {
  background: rgba(255, 255, 255, 0.7);
  padding: clamp(20px, 3vw, 40px);
  border-radius: 12px;
  border: 1px solid #4aa4ff;
  width: min(100%, 560px);
  box-shadow: 0 12px 30px rgba(0, 58, 136, 0.08);
}

.title {
  font-size: clamp(1.4rem, 2vw, 1.9rem);
  font-weight: 700;
  color: #0073ff;
  margin: 0 0 8px;
  text-align: center;
}

.subtitle {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin: 0 0 20px;
}

.subtitle-small {
  font-size: 12px;
  color: #666;
  margin: 0;
}

form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #333;
}

.field-error,
.form-error,
.success-message {
  font-size: 12px;
}

.form-error {
  color: #d93025;
  text-align: center;
}

.success-message {
  color: #0f7e2a;
  text-align: center;
}

label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

input {
  padding: 11px 12px;
  border: 1px solid #1ca4ff;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.3s ease;
  background-color: rgba(255, 255, 255, 0.75);
  color: #000;
  width: 100%;
}

input::placeholder {
  color: #888;
  opacity: 1;
}

input:focus {
  outline: none;
  border-color: #4caf50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.18);
}

.btn-login {
  padding: 12px;
  background: #1ca4ff;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-login:disabled,
.btn-secondary:disabled {
  cursor: not-allowed;
  background: #8ccfff;
}

.btn-login:hover,
.btn-secondary:hover {
  background: #1592e3;
}

.btn-login:active {
  transform: scale(0.98);
}

.btn-link {
  background: transparent;
  border: none;
  color: #0073ff;
  cursor: pointer;
  align-self: flex-end;
  font-size: 13px;
  text-decoration: underline;
  padding: 0;
}

.recovery-title {
  color: #0073ff;
  font-weight: 700;
  margin: 0;
}

.btn-secondary {
  padding: 10px;
  background: #1ca4ff;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.modal-card {
  width: min(100%, 520px);
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 12px;
  border: 1px solid #7ec3ff;
  background: #fff;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-close {
  border: none;
  background: transparent;
  color: #0073ff;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.toast {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 1200;
  min-width: 260px;
  max-width: min(92vw, 420px);
  padding: 12px 16px;
  border-radius: 10px;
  color: #fff;
  font-weight: 600;
  font-size: 13px;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
}

.toast--success {
  background: linear-gradient(135deg, #1d9f3a, #0f7e2a);
}

.toast--warning {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 520px) {
  .login-card {
    padding: 18px;
    border-radius: 10px;
  }

  .btn-link {
    align-self: flex-start;
  }

  .toast {
    top: 12px;
    right: 12px;
    left: 12px;
    min-width: auto;
  }
}
</style>
