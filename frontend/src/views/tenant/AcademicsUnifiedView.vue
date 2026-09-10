<script setup>
import { onMounted, ref } from 'vue'
import AcademicsView from './AcademicsViewFixed.vue'
import { academicsConfiguration } from '../../api/academics'

const configuration = ref(null)
const configurationError = ref('')

async function loadConfiguration() {
  try {
    configuration.value = await academicsConfiguration()
  } catch (e) {
    configurationError.value = e?.response?.data?.detail || 'Academic configuration could not be loaded.'
  }
}

onMounted(loadConfiguration)
</script>

<template>
  <div>
    <div v-if="configuration && !configurationError" class="container-fluid pt-3">
      <div class="alert alert-light border d-flex flex-wrap align-items-center justify-content-between gap-2 mb-0">
        <div><strong>{{ configuration.curriculum?.frameworks?.[0]?.framework_name || 'Academic configuration' }}</strong><span v-if="configuration.curriculum?.frameworks?.[0]?.version_name" class="text-muted ms-2">{{ configuration.curriculum.frameworks[0].version_name }}</span></div>
        <div class="small text-muted">Platform defaults are applied unless this school has an override.</div>
      </div>
    </div>
    <div v-else-if="configurationError" class="container-fluid pt-3"><div class="alert alert-warning">{{ configurationError }}</div></div>
    <AcademicsView />
  </div>
</template>
