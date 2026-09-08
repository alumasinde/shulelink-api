<script setup>
import { computed, onMounted, ref } from 'vue'
import { getApiError } from '../../api/client'
import { students, guardians } from '../../api/students'
import { portalAccounts } from '../../api/portalAccounts'

const activeTab = ref('students')
const loading = ref(true)
const loadingDetail = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const studentsRows = ref([])
const guardiansRows = ref([])
const selected = ref(null)
const account = ref(null)
const showProvision = ref(false)
const email = ref('')
const activation = ref(null)
const search = ref('')

const visibleRows = computed(() => {
  const rows = activeTab.value === 'students' ? studentsRows.value : guardiansRows.value
  const q = search.value.trim().toLowerCase()
  if (!q) return rows
  return rows.filter(row => [row.first_name, row.last_name, row.admission_number, row.email, row.phone].filter(Boolean).join(' ').toLowerCase().includes(q))
})

const selectedName = computed(() => selected.value ? [selected.value.first_name, selected.value.last_name].filter(Boolean).join(' ') : '')
const activationLink = computed(() => activation.value?.activation_token ? `${window.location.origin}/activate?token=${encodeURIComponent(activation.value.activation_token)}` : '')

function flash(message) {
  notice.value = message
  window.setTimeout(() => { notice.value = '' }, 3500)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [s, g] = await Promise.all([students.list({ limit: 200 }), guardians.list({ limit: 200 })])
    studentsRows.value = s
    guardiansRows.value = g
  } catch (e) {
    error.value = getApiError(e)
  } finally {
    loading.value = false
  }
}

async function selectRow(row) {
  selected.value = row
  account.value = null
  activation.value = null
  loadingDetail.value = true
  error.value = ''
  try {
    account.value = activeTab.value === 'students'
      ? await portalAccounts.student(row.id)
      : await portalAccounts.guardian(row.id)
  } catch (e) {
    error.value = getApiError(e)
  } finally {
    loadingDetail.value = false
  }
}

function changeTab(tab) {
  activeTab.value = tab
  selected.value = null
  account.value = null
  activation.value = null
  search.value = ''
}

function openProvision() {
  email.value = activeTab.value === 'guardians' ? selected.value?.email || '' : ''
  activation.value = null
  showProvision.value = true
}

async function provision() {
  if (!selected.value) return
  saving.value = true
  error.value = ''
  try {
    activation.value = activeTab.value === 'students'
      ? await portalAccounts.createStudent(selected.value.id, email.value.trim() || null)
      : await portalAccounts.createGuardian(selected.value.id, email.value.trim())
    account.value = await (activeTab.value === 'students' ? portalAccounts.student(selected.value.id) : portalAccounts.guardian(selected.value.id))
    showProvision.value = false
    flash(`${activeTab.value === 'students' ? 'Student' : 'Parent'} portal account created.`)
  } catch (e) {
    error.value = getApiError(e)
  } finally {
    saving.value = false
  }
}

async function resend() {
  if (!selected.value) return
  if (!confirm('Create a new activation link? The previous unused activation link will be invalidated.')) return
  saving.value = true
  error.value = ''
  try {
    activation.value = activeTab.value === 'students'
      ? await portalAccounts.resendStudent(selected.value.id)
      : await portalAccounts.resendGuardian(selected.value.id)
    account.value = await (activeTab.value === 'students' ? portalAccounts.student(selected.value.id) : portalAccounts.guardian(selected.value.id))
    flash('A new activation link has been generated.')
  } catch (e) {
    error.value = getApiError(e)
  } finally {
    saving.value = false
  }
}

async function copyActivationLink() {
  if (!activationLink.value) return
  await navigator.clipboard.writeText(activationLink.value)
  flash('Activation link copied.')
}

function openActivation() {
  if (activationLink.value) window.open(activationLink.value, '_blank', 'noopener,noreferrer')
}

function statusClass(status) {
  return {
    active: 'text-bg-success',
    pending: 'text-bg-warning',
    expired: 'text-bg-danger',
    not_created: 'text-bg-secondary',
  }[status] || 'text-bg-secondary'
}

function statusLabel(status) {
  return ({ not_created: 'Not created', pending: 'Activation pending', active: 'Active', expired: 'Activation expired' })[status] || status
}

onMounted(load)
</script>

<template>
  <div class="dashboard-page portal-accounts-page">
    <section class="dashboard-heading">
      <div>
        <div class="eyebrow">PORTAL ACCOUNT MANAGEMENT</div>
        <h1>Portal Accounts</h1>
        <p>Create and manage secure login access for parents and students.</p>
      </div>
      <router-link to="/school/students" class="btn btn-light">
        <i class="bi bi-arrow-left me-2"></i>Students
      </router-link>
    </section>

    <div v-if="notice" class="alert alert-success border-0 shadow-sm">{{ notice }}</div>
    <div v-if="error" class="alert alert-danger border-0 shadow-sm">{{ error }}</div>

    <section class="metric-grid mb-4">
      <div class="metric-card">
        <div class="metric-icon"><i class="bi bi-mortarboard"></i></div>
        <div><span>Students</span><strong>{{ studentsRows.length }}</strong><small>Portal identities</small></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon"><i class="bi bi-person-hearts"></i></div>
        <div><span>Parents</span><strong>{{ guardiansRows.length }}</strong><small>Guardian identities</small></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon"><i class="bi bi-shield-check"></i></div>
        <div><span>Activation</span><strong>24h</strong><small>Activation link lifetime</small></div>
      </div>
    </section>

    <div class="row g-4">
      <div class="col-xl-7">
        <section class="dashboard-card h-100">
          <div class="card-heading">
            <div><h2>Portal users</h2><p>Select an existing student or parent to manage their portal account.</p></div>
          </div>
          <div class="account-tabs">
            <button :class="['account-tab', { active: activeTab === 'students' }]" @click="changeTab('students')"><i class="bi bi-mortarboard me-2"></i>Students</button>
            <button :class="['account-tab', { active: activeTab === 'guardians' }]" @click="changeTab('guardians')"><i class="bi bi-person-hearts me-2"></i>Parents</button>
          </div>
          <div class="search-box mb-3"><i class="bi bi-search"></i><input v-model="search" placeholder="Search by name, admission number or contact..." /></div>
          <div v-if="loading" class="py-5 text-center"><span class="spinner-border text-primary"></span></div>
          <div v-else-if="!visibleRows.length" class="empty-state py-5"><i class="bi bi-people"></i><h3>No records found</h3><p>There are no matching records in this school.</p></div>
          <div v-else class="account-user-list">
            <button v-for="row in visibleRows" :key="row.id" class="account-user-row" :class="{ selected: selected?.id === row.id }" @click="selectRow(row)">
              <span class="mini-avatar">{{ row.first_name?.[0] }}{{ row.last_name?.[0] }}</span>
              <span class="account-user-copy"><strong>{{ row.first_name }} {{ row.last_name }}</strong><small>{{ activeTab === 'students' ? row.admission_number : (row.phone || row.email || 'Guardian') }}</small></span>
              <i class="bi bi-chevron-right text-muted"></i>
            </button>
          </div>
        </section>
      </div>

      <div class="col-xl-5">
        <section class="dashboard-card h-100">
          <div v-if="!selected" class="empty-state py-5"><i class="bi bi-person-badge"></i><h3>Select a user</h3><p>Choose a student or parent to view their portal account.</p></div>
          <template v-else>
            <div class="detail-head mb-4">
              <div class="student-avatar"><span>{{ selected.first_name?.[0] }}{{ selected.last_name?.[0] }}</span></div>
              <div><div class="eyebrow">{{ activeTab === 'students' ? selected.admission_number : 'PARENT / GUARDIAN' }}</div><h2>{{ selectedName }}</h2></div>
            </div>
            <div v-if="loadingDetail" class="py-5 text-center"><span class="spinner-border text-primary"></span></div>
            <template v-else-if="account">
              <div class="account-status-panel">
                <div><small>Portal status</small><strong><span class="badge" :class="statusClass(account.status)">{{ statusLabel(account.status) }}</span></strong></div>
                <i class="bi" :class="account.status === 'active' ? 'bi-check-circle-fill' : 'bi-person-lock'"></i>
              </div>
              <div class="detail-section">
                <h3>Login details</h3>
                <div class="login-detail-row"><span>Login</span><strong>{{ account.login_identifier || account.email || 'Not assigned' }}</strong></div>
                <div v-if="account.email" class="login-detail-row"><span>Email</span><strong>{{ account.email }}</strong></div>
                <div v-if="account.activation_expires_at" class="login-detail-row"><span>Activation expires</span><strong>{{ new Date(account.activation_expires_at).toLocaleString() }}</strong></div>
              </div>
              <div class="detail-section" v-if="activation">
                <h3>Activation link</h3>
                <div class="activation-box"><code>{{ activationLink }}</code></div>
                <div class="d-flex gap-2 mt-2"><button class="btn btn-primary btn-sm" @click="openActivation"><i class="bi bi-box-arrow-up-right me-1"></i>Open activation</button><button class="btn btn-outline-secondary btn-sm" @click="copyActivationLink"><i class="bi bi-copy me-1"></i>Copy link</button></div>
                <div class="small text-muted mt-2">The activation link is shown only after it is generated. Give it to the user securely.</div>
              </div>
              <div class="account-actions">
                <button v-if="account.status === 'not_created'" class="btn btn-primary w-100" @click="openProvision"><i class="bi bi-person-plus me-2"></i>Create portal account</button>
                <button v-else-if="account.status === 'pending' || account.status === 'expired'" class="btn btn-primary w-100" :disabled="saving" @click="resend"><i class="bi bi-arrow-repeat me-2"></i>{{ saving ? 'Generating…' : 'Generate new activation link' }}</button>
                <div v-else class="alert alert-success mb-0"><i class="bi bi-check-circle me-2"></i>This portal account is active.</div>
              </div>
            </template>
          </template>
        </section>
      </div>
    </div>

    <div v-if="showProvision" class="modal-backdrop-custom">
      <div class="modal-card">
        <div class="modal-head"><div><div class="eyebrow">{{ activeTab === 'students' ? 'STUDENT PORTAL' : 'PARENT PORTAL' }}</div><h2>Create portal account</h2><p>{{ selectedName }} will receive a secure activation link.</p></div><button class="btn btn-light" @click="showProvision=false"><i class="bi bi-x-lg"></i></button></div>
        <label class="form-label">{{ activeTab === 'students' ? 'Email (optional)' : 'Parent email *' }}</label>
        <input v-model="email" class="form-control" type="email" :required="activeTab === 'guardians'" :placeholder="activeTab === 'students' ? 'Leave empty to use the student login ID' : 'parent@example.com'">
        <div class="form-text mb-4">The user sets their own password during activation. Passwords are not stored or displayed by this screen.</div>
        <div class="d-flex justify-content-end gap-2"><button class="btn btn-light" @click="showProvision=false">Cancel</button><button class="btn btn-primary" :disabled="saving" @click="provision">{{ saving ? 'Creating…' : 'Create account' }}</button></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.account-tabs{display:flex;gap:.35rem;border-bottom:1px solid #e9ecef;margin-bottom:1rem}.account-tab{border:0;background:transparent;padding:.7rem 1rem;color:#6c757d;font-weight:600;border-bottom:2px solid transparent}.account-tab.active{color:#0d6efd;border-bottom-color:#0d6efd}.account-user-list{display:flex;flex-direction:column;gap:.45rem;max-height:520px;overflow:auto}.account-user-row{display:flex;align-items:center;gap:.8rem;width:100%;border:1px solid #edf0f3;background:#fff;border-radius:.8rem;padding:.75rem;text-align:left}.account-user-row:hover,.account-user-row.selected{border-color:#86b7fe;background:#f8fbff}.account-user-copy{display:flex;flex-direction:column;flex:1}.account-user-copy small{color:#6c757d;margin-top:.15rem}.account-status-panel{display:flex;align-items:center;justify-content:space-between;padding:1rem;border-radius:.8rem;background:#f8f9fa;margin-bottom:1.25rem}.account-status-panel small{display:block;color:#6c757d;margin-bottom:.35rem}.account-status-panel>i{font-size:1.5rem;color:#198754}.login-detail-row{display:flex;justify-content:space-between;gap:1rem;padding:.7rem 0;border-bottom:1px solid #f0f1f3}.login-detail-row span{color:#6c757d}.login-detail-row strong{text-align:right;word-break:break-word}.activation-box{background:#f8f9fa;border:1px solid #e9ecef;border-radius:.6rem;padding:.75rem;max-height:100px;overflow:auto}.activation-box code{font-size:.75rem;word-break:break-all}.account-actions{margin-top:1.25rem}.modal-wide{max-width:760px}.modal-backdrop-custom{position:fixed;inset:0;background:rgba(15,23,42,.48);display:flex;align-items:center;justify-content:center;padding:1rem;z-index:1050}.modal-card{width:min(100%,560px);background:#fff;border-radius:1rem;box-shadow:0 1rem 3rem rgba(0,0,0,.18);padding:1.5rem}.modal-head{display:flex;justify-content:space-between;gap:1rem;margin-bottom:1.25rem}.modal-head h2{margin:.25rem 0}.modal-head p{margin:0;color:#6c757d}.eyebrow{font-size:.7rem;font-weight:700;letter-spacing:.08em;color:#6c757d}.mini-avatar,.student-avatar{display:flex;align-items:center;justify-content:center;border-radius:50%;background:#e9f2ff;color:#0d6efd;font-weight:700}.mini-avatar{width:40px;height:40px;flex:0 0 40px}.student-avatar{width:52px;height:52px;flex:0 0 52px}.detail-head{display:flex;align-items:center;gap:.9rem}.detail-section{border-top:1px solid #edf0f3;padding-top:1rem;margin-top:1rem}.detail-section h3{font-size:.95rem;margin-bottom:.7rem}.search-box{display:flex;align-items:center;gap:.6rem;border:1px solid #dee2e6;border-radius:.6rem;padding:.55rem .75rem}.search-box input{border:0;outline:0;width:100%;background:transparent}.empty-state{text-align:center;color:#6c757d}.empty-state i{font-size:2rem;display:block;margin-bottom:.6rem}.empty-state h3{font-size:1rem;color:#212529}.empty-state p{margin-bottom:0}
</style>
