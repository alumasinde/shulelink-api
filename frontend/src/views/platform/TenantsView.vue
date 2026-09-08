<script setup>
import { onMounted, ref } from "vue";
import { createTenant, createTenantUser, listTenants } from "../../api/tenants";
import { getApiError } from "../../api/client";

const tenants = ref([]);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const success = ref("");
const showCreate = ref(false);
const showUser = ref(false);
const selected = ref(null);
const form = ref({ name: "", slug: "", database_mode: "shared" });
const userForm = ref({ email: "", first_name: "", last_name: "", password: "", role_code: "school_admin" });

async function load() { loading.value = true; error.value = ""; try { tenants.value = await listTenants(); } catch (e) { error.value = getApiError(e); } finally { loading.value = false; } }
async function saveTenant() { saving.value = true; error.value = ""; success.value = ""; try { await createTenant(form.value); success.value = "School created successfully."; showCreate.value = false; form.value = { name: "", slug: "", database_mode: "shared" }; await load(); } catch (e) { error.value = getApiError(e); } finally { saving.value = false; } }
function openUser(tenant) { selected.value = tenant; showUser.value = true; error.value = ""; success.value = ""; }
async function saveUser() { saving.value = true; error.value = ""; try { await createTenantUser(selected.value.id, userForm.value); success.value = `User created for ${selected.value.name}.`; showUser.value = false; userForm.value = { email: "", first_name: "", last_name: "", password: "", role_code: "school_admin" }; } catch (e) { error.value = getApiError(e); } finally { saving.value = false; } }
function openSchool(tenant) { window.open(`http://${tenant.host}:5173/login`, "_blank", "noopener,noreferrer"); }
onMounted(load);
</script>

<template>
  <div class="page-wrap">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4"><div><span class="eyebrow">PLATFORM / SCHOOLS</span><h1 class="h3 fw-bold mt-2 mb-1">Schools</h1><p class="text-muted mb-0">Create and manage ShuleLink tenant environments.</p></div><button class="btn btn-primary" @click="showCreate = true"><i class="bi bi-plus-lg me-2"></i>New school</button></div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div><div v-if="success" class="alert alert-success">{{ success }}</div>
    <div class="card border-0 shadow-sm overflow-hidden"><div class="table-responsive"><table class="table align-middle mb-0"><thead><tr><th>School</th><th>Domain</th><th>Database</th><th>Status</th><th class="text-end">Actions</th></tr></thead><tbody>
      <tr v-if="loading"><td colspan="5" class="text-center py-5"><span class="spinner-border spinner-border-sm"></span></td></tr><tr v-else-if="!tenants.length"><td colspan="5" class="text-center py-5 text-muted">No schools yet. Create your first school.</td></tr>
      <tr v-for="tenant in tenants" :key="tenant.id"><td><div class="fw-semibold">{{ tenant.name }}</div><div class="tiny text-muted">{{ tenant.slug }}</div></td><td><code>{{ tenant.host }}</code></td><td><span class="badge rounded-pill text-bg-light border">{{ tenant.database_mode }}</span></td><td><span class="status-dot" :class="tenant.status"></span>{{ tenant.status }}</td><td class="text-end"><div class="btn-group"><button class="btn btn-sm btn-light border" @click="openUser(tenant)"><i class="bi bi-person-plus me-1"></i>User</button><button class="btn btn-sm btn-light border" @click="openSchool(tenant)"><i class="bi bi-box-arrow-up-right me-1"></i>Open</button></div></td></tr>
    </tbody></table></div></div>

    <div v-if="showCreate" class="modal-backdrop-custom"><div class="modal-card"><div class="d-flex justify-content-between mb-4"><div><h2 class="h5 fw-bold mb-1">Create school</h2><p class="text-muted small mb-0">Create a new tenant environment.</p></div><button class="btn-close" @click="showCreate=false"></button></div><form @submit.prevent="saveTenant"><label class="form-label">School name</label><input v-model="form.name" class="form-control mb-3" required placeholder="Demo Primary School"><label class="form-label">Slug</label><input v-model="form.slug" class="form-control mb-3" required placeholder="demo-primary"><div class="form-text mb-3">Local address will be <strong>{{ form.slug || 'slug' }}.localhost</strong></div><label class="form-label">Database mode</label><select v-model="form.database_mode" class="form-select mb-4"><option value="shared">Shared</option><option value="dedicated">Dedicated</option></select><div class="d-flex justify-content-end gap-2"><button type="button" class="btn btn-light" @click="showCreate=false">Cancel</button><button class="btn btn-primary" :disabled="saving">{{ saving ? 'Creating…' : 'Create school' }}</button></div></form></div></div>
    <div v-if="showUser" class="modal-backdrop-custom"><div class="modal-card"><div class="d-flex justify-content-between mb-4"><div><h2 class="h5 fw-bold mb-1">Create school user</h2><p class="text-muted small mb-0">{{ selected?.name }}</p></div><button class="btn-close" @click="showUser=false"></button></div><form @submit.prevent="saveUser"><div class="row g-3"><div class="col-md-6"><label class="form-label">First name</label><input v-model="userForm.first_name" class="form-control" required></div><div class="col-md-6"><label class="form-label">Last name</label><input v-model="userForm.last_name" class="form-control" required></div><div class="col-12"><label class="form-label">Email</label><input v-model="userForm.email" type="email" class="form-control" required></div><div class="col-md-8"><label class="form-label">Temporary password</label><input v-model="userForm.password" type="password" minlength="10" class="form-control" required></div><div class="col-md-4"><label class="form-label">Role</label><select v-model="userForm.role_code" class="form-select"><option value="school_admin">School admin</option><option value="teacher">Teacher</option><option value="guardian">Guardian</option></select></div></div><div class="d-flex justify-content-end gap-2 mt-4"><button type="button" class="btn btn-light" @click="showUser=false">Cancel</button><button class="btn btn-primary" :disabled="saving">{{ saving ? 'Creating…' : 'Create user' }}</button></div></form></div></div>
  </div>
</template>
