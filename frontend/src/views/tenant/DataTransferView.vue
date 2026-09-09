<script setup>
import { ref } from 'vue'
import { getApiError } from '../../api/client'
import { dataTransfer } from '../../api/dataTransfer'

const file = ref(null)
const mode = ref('create')
const busy = ref(false)
const error = ref('')
const result = ref(null)

function selectFile(event) {
  file.value = event.target.files?.[0] || null
  result.value = null
  error.value = ''
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

async function template() {
  busy.value = true
  error.value = ''
  try {
    download(await dataTransfer.template(), 'ShuleLink_School_Structure_Template.xlsx')
  } catch (e) {
    error.value = getApiError(e)
  } finally {
    busy.value = false
  }
}

async function exportData() {
  busy.value = true
  error.value = ''
  try {
    download(await dataTransfer.exportSchoolStructure(), 'ShuleLink_School_Structure_Export.xlsx')
  } catch (e) {
    error.value = getApiError(e)
  } finally {
    busy.value = false
  }
}

async function importData() {
  if (!file.value) {
    error.value = 'Select an .xlsx file first.'
    return
  }
  busy.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await dataTransfer.importSchoolStructure(file.value, mode.value)
  } catch (e) {
    error.value = getApiError(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page-wrap">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div>
        <span class="eyebrow">DATA MANAGEMENT</span>
        <h1 class="h3 fw-bold mt-2 mb-1">Import & Export</h1>
        <p class="text-muted mb-0">Move School Structure data in and out of ShuleLink using the official Excel workbook format.</p>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-primary" :disabled="busy" @click="template"><i class="bi bi-file-earmark-arrow-down me-2"></i>Download Template</button>
        <button class="btn btn-primary" :disabled="busy" @click="exportData"><i class="bi bi-download me-2"></i>Export Current Data</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <div class="row g-4">
      <div class="col-lg-7">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white border-0 p-4">
            <h2 class="h5 fw-bold mb-1">Import School Structure</h2>
            <p class="text-muted mb-0">The import is validated before anything is committed. A failed import is rolled back.</p>
          </div>
          <div class="card-body p-4 border-top">
            <div class="mb-3">
              <label class="form-label fw-semibold">Excel workbook</label>
              <input class="form-control" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="selectFile">
              <div class="form-text">Use the ShuleLink template or an existing ShuleLink School Structure export.</div>
            </div>
            <div class="mb-4">
              <label class="form-label fw-semibold">Import mode</label>
              <select v-model="mode" class="form-select">
                <option value="create">Create New — reject duplicates</option>
                <option value="upsert">Upsert — create missing and update matching records</option>
              </select>
            </div>
            <button class="btn btn-primary" :disabled="busy || !file" @click="importData">
              <span v-if="busy" class="spinner-border spinner-border-sm me-2"></span>
              <i v-else class="bi bi-upload me-2"></i>
              {{ busy ? 'Processing…' : 'Import Workbook' }}
            </button>
          </div>
        </div>
      </div>

      <div class="col-lg-5">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white border-0 p-4">
            <h2 class="h5 fw-bold mb-1">Import Order</h2>
            <p class="text-muted mb-0">Parent records are resolved automatically.</p>
          </div>
          <div class="card-body p-4 border-top">
            <ol class="mb-0">
              <li>Campuses</li>
              <li>Academic Years</li>
              <li>Academic Terms</li>
              <li>Departments</li>
              <li>Class Levels</li>
              <li>Streams</li>
              <li>Subjects</li>
              <li>Class Subjects</li>
              <li>School Settings</li>
            </ol>
            <div class="alert alert-light border mt-4 mb-0 small">
              Imports never delete existing rows. Upsert uses school-level natural keys such as codes and names.
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="result" class="card border-0 shadow-sm mt-4">
      <div class="card-body p-4">
        <div v-if="result.valid" class="alert alert-success mb-0">
          <strong>Import completed.</strong>
          Created: {{ result.created }} · Updated: {{ result.updated }}
        </div>
        <div v-else>
          <div class="alert alert-danger">
            <strong>Import was not committed.</strong>
            {{ result.error_count }} error(s) found.
          </div>
          <div class="table-responsive">
            <table class="table table-sm align-middle">
              <thead><tr><th>Sheet</th><th>Row</th><th>Field</th><th>Error</th></tr></thead>
              <tbody>
                <tr v-for="(item, index) in result.errors" :key="index">
                  <td>{{ item.sheet }}</td><td>{{ item.row ?? '—' }}</td><td>{{ item.field }}</td><td>{{ item.message }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
