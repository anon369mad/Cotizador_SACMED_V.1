<template>
  <div class="login-container">
    <div class="login-card">
      <h1 class="title">Sistema de Cotizaciones</h1>
      <p class="subtitle">Ingresa tus credenciales para continuar</p>
      
      <form @submit.prevent="login">
        <div class="form-group">
          <label for="email">Correo Electrónico</label>
          <input 
            id="email"
            v-model="email" 
            type="email"
            placeholder="tu@email.com" 
            required
          />
        </div>

        <div class="form-group">
          <label for="password">Contraseña</label>
          <input 
            id="password"
            v-model="password" 
            type="password" 
            placeholder="Ingresa tu contraseña"
            required 
          />
        </div>
        <button class="btn-login" @click="$emit('login-ok')">Iniciar Sesión</button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      email: '',
      password: ''
    }
  },
  methods: {
    async login() {
      const res = await fetch('http://localhost:8000/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: this.email,
          password: this.password
        })
      })

      const data = await res.json()
      console.log(data)
    }
  }
}
</script>
<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f500;
}

.login-card {
  background: rgba(255, 255, 255, 0);
  padding: 50px;
  border-radius: 2px;
  border: 1px solid #4aa4ff;
  width: 100%;
  max-width: 500px;
}

.title {
  font-size: 28px;
  font-weight: bold;
  color: #0073ff;
  margin: 0 0 10px 0;
  text-align: center;
}

.subtitle {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin: 0 0 30px 0;
}

form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color:#333;
}

label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

input {
  padding: 12px;
  border: 1px solid #1ca4ff;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.3s ease;
  background-color: rgba(255, 255, 255, 0);
  color: #000; /* texto en negro */
}

input::placeholder {
  color: #888; /* placeholder legible */
  opacity: 1;
}

input:focus {
  outline: none;
  border-color: #4CAF50;
  box-shadow: 0 0 5px rgba(76, 175, 80, 0.2);
}

.btn-login {
  padding: 12px;
  background: #1ca4ff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-login:hover {
  background: #2bf8ff;
}

.btn-login:active {
  transform: scale(0.98);
}
</style>