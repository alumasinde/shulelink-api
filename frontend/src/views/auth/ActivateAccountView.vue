<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, getApiError } from '../../api/client'

const route = useRoute()
const router = useRouter()
const token = ref(String(route.query.token || ''))
const password = ref('')
const confirm = ref('')
const error = ref('')
const message = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  message.value = ''
  if (password.value.length < 8) { error.value = 'Password must be at least 8 characters.'; return }
  if (!/[A-Z]/.test(password.value) || !/[a-z]/.test(password.value) || !/[0-9]/.test(password.value)) { error.value = 'Use at least one uppercase letter, one lowercase letter and one number.'; return }
  if (password.value !== confirm.value) { error.value = 'Passwords do not match.'; return }
  loading.value = true
  try {
    const { data } = await api.post('/auth/activate', { token: token.value.trim(), password: password.value })
    message.value = data.message
    setTimeout(() => router.replace('/login'), 1000)
  } catch (err) { error.value = getApiError(err, 'Unable to activate the account.') }
  finally { loading.value = false }
}
</script>

<template>
  <div class="login-page">
    <div class="login-panel">
      <div class="login-brand"><span class="brand-mark">S</span><span>ShuleLink</span></div>
      <div class="mt-5 mb-4"><span class="eyebrow">ACCOUNT ACTIVATION</span><h1 class="h3 fw-bold mt-2 mb-2">Set your password</h1><p class="text-muted mb-0">Activate your school portal account securely.</p></div>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <div v-if="message" class="alert alert-success">{{ message }}</div>
      <form @submit.prevent="submit">
        <label class="form-label">Activation token</label>
        <input v-model="token" class="form-control mb-3" required>
        <label class="form-label">New password</label>
        <input v-model="password" class="form-control mb-2" type="password" minlength="8" autocomplete="new-password" required>
        <div class="form-text mb-3">Minimum 8 characters with an uppercase letter, lowercase letter and number.</div>
        <label class="form-label">Confirm password</label>
        <input v-model="confirm" class="form-control mb-4" type="password" minlength="8" autocomplete="new-password" required>
        <button class="btn btn-primary w-100" :disabled="loading">{{ loading ? 'Activating…' : 'Activate account' }}</button>
      </form>
    </div>
  </div>
</template>
