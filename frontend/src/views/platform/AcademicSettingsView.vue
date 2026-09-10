<script setup>
import { onMounted, ref } from "vue";
import { listPlatformAcademicSettings, updatePlatformAcademicSetting } from "../../api/platformAcademicSettings";
import { getApiError } from "../../api/client";

const settings = ref([]);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const success = ref("");

function cloneValue(value) {
  if (value === null || value === undefined) return value;
  return structuredClone(value);
}

function prepare(item) {
  return {
    ...item,
    draft: item.value_type === "json" ? cloneValue(item.setting_value) : item.setting_value === null || item.setting_value === undefined ? "" : String(item.setting_value),
  };
}

function isEducationStructure(item) {
  return item.setting_key === "academic.default_education_structure" && Array.isArray(item.draft);
}

function addEducationLevel(item) {
  item.draft.push({ code: "", name: "", sequence: item.draft.length + 1 });
}

function removeEducationLevel(item, index) {
  if (!window.confirm("Remove this education level from the platform default?")) return;
  item.draft.splice(index, 1);
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    settings.value = (await listPlatformAcademicSettings()).map(prepare);
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    loading.value = false;
  }
}

function parse(item) {
  if (item.value_type === "integer") return Number(item.draft);
  if (item.value_type === "boolean") return item.draft === true || item.draft === "true" || item.draft === "1";
  if (item.value_type === "json") return cloneValue(item.draft);
  if (item.draft === "null") return null;
  return item.draft;
}

async function save(item) {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    const updated = await updatePlatformAcademicSetting(item.id, { setting_value: parse(item), value_type: item.value_type });
    Object.assign(item, prepare(updated));
    success.value = "Platform academic defaults updated. Schools will receive the new defaults unless they override the setting locally.";
  } catch (e) {
    error.value = e instanceof Error ? e.message : getApiError(e);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page-wrap academic-settings-page">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div>
        <span class="eyebrow">PLATFORM / ACADEMICS</span>
        <h1 class="h3 fw-bold mt-2 mb-1">Academic defaults</h1>
        <p class="text-muted mb-0">Configure platform-wide academic behaviour. Schools inherit these values and may override supported settings.</p>
      </div>
      <button class="btn btn-outline-primary" :disabled="loading" @click="load"><i class="bi bi-arrow-clockwise me-1"></i>Refresh</button>
    </div>

    <div v-if="error" class="alert alert-danger border-0 shadow-sm">{{ error }}</div>
    <div v-if="success" class="alert alert-success border-0 shadow-sm">{{ success }}</div>

    <div class="info-banner mb-4"><div class="info-icon"><i class="bi bi-sliders2"></i></div><div><strong>Platform defaults are configurable</strong><p>These values provide sensible starting points for schools; they are not hardcoded Kenyan education rules. Curriculum, grade names, subjects, teacher eligibility and timetable policies remain configurable.</p></div></div>

    <div v-if="loading" class="card border-0 shadow-sm"><div class="card-body text-center py-5"><span class="spinner-border spinner-border-sm me-2"></span>Loading academic defaults...</div></div>
    <div v-else class="vstack gap-3">
      <div v-for="item in settings" :key="item.id" class="setting-card">
        <div class="setting-header">
          <div class="d-flex align-items-start gap-3">
            <div class="setting-icon"><i class="bi" :class="item.value_type === 'json' ? 'bi-braces' : item.value_type === 'boolean' ? 'bi-toggle-on' : 'bi-input-cursor-text'"></i></div>
            <div><div class="setting-key">{{ item.setting_key }}</div><div class="small text-muted mt-1">{{ item.description }}</div></div>
          </div>
          <span class="badge text-bg-light border">{{ item.value_type }}</span>
        </div>

        <div class="setting-body">
          <template v-if="isEducationStructure(item)">
            <div class="structured-toolbar"><div><strong>Education structure</strong><div class="small text-muted">Add and order the education levels schools will inherit by default.</div></div><button class="btn btn-outline-primary btn-sm" @click="addEducationLevel(item)"><i class="bi bi-plus-lg me-1"></i>Add level</button></div>
            <div v-if="!item.draft.length" class="empty-structure">No default levels configured yet.</div>
            <div v-else class="structure-list">
              <div v-for="(level, index) in item.draft" :key="index" class="structure-row">
                <div class="sequence">{{ index + 1 }}</div>
                <div class="row g-2 flex-grow-1">
                  <div class="col-md-4"><label class="form-label">Code</label><input v-model="level.code" class="form-control" placeholder="e.g. primary"></div>
                  <div class="col-md-5"><label class="form-label">Name</label><input v-model="level.name" class="form-control" placeholder="e.g. Primary School"></div>
                  <div class="col-md-3"><label class="form-label">Sequence</label><input v-model.number="level.sequence" type="number" min="0" class="form-control"></div>
                </div>
                <button class="btn btn-sm btn-outline-danger remove-btn" type="button" title="Remove level" @click="removeEducationLevel(item, index)"><i class="bi bi-trash"></i></button>
              </div>
            </div>
          </template>

          <template v-else-if="item.value_type === 'boolean'">
            <div class="boolean-setting"><div><strong>{{ item.draft === true || item.draft === 'true' ? 'Enabled' : 'Disabled' }}</strong><div class="small text-muted">Choose whether this platform behaviour is enabled by default.</div></div><select v-model="item.draft" class="form-select setting-select"><option :value="true">Enabled</option><option :value="false">Disabled</option></select></div>
          </template>

          <template v-else>
            <input v-model="item.draft" class="form-control" :type="item.value_type === 'integer' ? 'number' : 'text'">
          </template>

          <div class="d-flex justify-content-end mt-3"><button class="btn btn-primary btn-sm" :disabled="saving" @click="save(item)"><span v-if="saving" class="spinner-border spinner-border-sm me-2"></span><i v-else class="bi bi-save me-1"></i>Save default</button></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.info-banner { display: flex; align-items: flex-start; gap: 12px; background: #e9f8ff; border: 1px solid #b9e9f8; border-radius: 12px; padding: 14px 16px; color: #155e75; }
.info-icon { width: 35px; height: 35px; flex: 0 0 35px; border-radius: 9px; background: #d7f3fb; display: flex; align-items: center; justify-content: center; }
.info-banner strong { font-size: .78rem; }
.info-banner p { margin: 3px 0 0; font-size: .72rem; line-height: 1.55; }
.setting-card { background: #fff; border: 1px solid #e8edf3; border-radius: 14px; box-shadow: 0 3px 15px rgba(23,32,51,.035); overflow: hidden; }
.setting-header { padding: 17px 18px; display: flex; align-items: flex-start; justify-content: space-between; gap: 15px; border-bottom: 1px solid #edf1f5; }
.setting-icon { width: 38px; height: 38px; flex: 0 0 38px; border-radius: 10px; background: #eef4ff; color: var(--sl-primary); display: flex; align-items: center; justify-content: center; }
.setting-key { font-size: .8rem; font-weight: 700; }
.setting-body { padding: 18px; }
.structured-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 15px; margin-bottom: 13px; }
.structured-toolbar strong { font-size: .8rem; }
.structure-list { display: flex; flex-direction: column; gap: 9px; }
.structure-row { display: flex; align-items: flex-end; gap: 10px; padding: 12px; border: 1px solid #edf1f5; border-radius: 11px; background: #fbfcfe; }
.sequence { width: 27px; height: 27px; flex: 0 0 27px; border-radius: 8px; background: #eaf1ff; color: var(--sl-primary); display: flex; align-items: center; justify-content: center; font-size: .68rem; font-weight: 700; margin-bottom: 7px; }
.form-label { font-size: .7rem; font-weight: 600; color: #4b5563; margin-bottom: 4px; }
.form-control, .form-select { font-size: .78rem; }
.remove-btn { margin-bottom: 1px; }
.empty-structure { padding: 25px; text-align: center; border: 1px dashed #dce3ec; border-radius: 11px; color: #8a94a3; font-size: .75rem; }
.boolean-setting { min-height: 60px; display: flex; align-items: center; justify-content: space-between; gap: 15px; }
.boolean-setting strong { font-size: .82rem; }
.setting-select { max-width: 180px; }
@media (max-width: 767.98px) { .structure-row { align-items: flex-start; flex-wrap: wrap; } .sequence { margin-top: 3px; } .remove-btn { margin-left: auto; } .structured-toolbar { align-items: flex-start; } }
</style>
