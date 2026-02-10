<template>
  <div class="login-container">
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

        <button type="button" class="btn-link" @click="toggleRecoveryForm">
          ¿Olvidaste tu contraseña?
        </button>

        <div v-if="showRecovery" class="recovery-panel">
          <p class="recovery-title">Recuperar contraseña</p>
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

          <div v-if="recoveryToken" class="token-box">
            <p><strong>Token generado:</strong> {{ recoveryToken }}</p>
            <p class="token-help">Cópialo y úsalo para establecer la nueva contraseña.</p>
          </div>

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

        <p v-if="formError" class="form-error">{{ formError }}</p>
        <button class="btn-login" type="submit" :disabled="loading">
          {{ loading ? 'Ingresando...' : 'Iniciar Sesión' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      email: '',
      password: '',
      errors: {},
      formError: '',
      loading: false,
      showRecovery: false,
      recoveryEmail: '',
      recoveryToken: '',
      resetToken: '',
      newPassword: '',
      recoveryLoading: false,
      resetLoading: false,
      recoveryError: '',
      recoveryMessage: ''
    }
  },
  methods: {
    clearFieldError(field) {
      if (this.errors[field]) {
        this.errors = { ...this.errors, [field]: '' }
      }
    },
    toggleRecoveryForm() {
      this.showRecovery = !this.showRecovery
      this.recoveryError = ''
      this.recoveryMessage = ''
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
      this.recoveryToken = ''

      if (!this.recoveryEmail.trim()) {
        this.recoveryError = 'Debes ingresar un correo para recuperar la contraseña.'
        return
      }

      this.recoveryLoading = true
      try {
        const res = await fetch('http://localhost:8000/password-recovery', {
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

        this.recoveryToken = data.recovery_token
        this.resetToken = data.recovery_token
        this.recoveryMessage = data.message
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
        const res = await fetch('http://localhost:8000/password-reset', {
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
      } catch (error) {
        this.recoveryError = 'No fue posible conectar con el servicio de recuperación.'
      } finally {
        this.resetLoading = false
      }
    },
    async login() {
      this.formError = ''

      if (!this.validateForm()) {
        return
      }

      this.loading = true

      try {
        // Se valida el usuario contra el sistema existente.
        const res = await fetch('http://localhost:8000/login', {
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
            this.formError = 'Credenciales inválidas.'
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

.recovery-panel {
  border: 1px solid #7ec3ff;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.token-box {
  background: rgba(28, 164, 255, 0.1);
  border: 1px dashed #1ca4ff;
  border-radius: 8px;
  padding: 10px;
  color: #004f9f;
}

.token-help {
  margin: 6px 0 0;
  font-size: 12px;
}

@media (max-width: 520px) {
  .login-card {
    padding: 18px;
    border-radius: 10px;
  }

  .btn-link {
    align-self: flex-start;
  }
}
</style>
