<script setup>
import { computed, onMounted, ref } from "vue";
import { curriculum } from "../../api/curriculum";
import { getApiError } from "../../api/client";

const templates = ref([]);
const selected = ref(null);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const notice = ref("");
const activeSection = ref("overview");
const form = ref({ name: "", description: "", country_code: "", framework_code: "", effective_from: "", effective_to: "" });
const document = ref(emptyDocument());

function emptyDocument() {
  return { levels: [], grades: [], learning_areas: [], subjects: [], offerings: [], pathways: [], tracks: [], combinations: [] };
}

const sections = [
  ["levels", "Education levels", "Define the broad education stages."],
  ["grades", "Grades", "Map grades to an education level."],
  ["learning_areas", "Learning areas", "Group related subjects into learning areas."],
  ["subjects", "Subjects", "Define the subjects schools can offer."],
  ["offerings", "Subject offerings", "Set grade, pathway and weekly-period requirements."],
  ["pathways", "Pathways", "Define senior-school or curriculum pathways."],
  ["tracks", "Tracks", "Define tracks within a pathway."],
  ["combinations", "Subject combinations", "Define selectable subject combinations."],
];

const counts = computed(() => selected.value?.counts || {});
const isDraft = computed(() => selected.value?.status === "draft");
const sectionTitle = computed(() => sections.find(([key]) => key === activeSection.value)?.[1] || "Overview");
const sectionDescription = computed(() => sections.find(([key]) => key === activeSection.value)?.[2] || "Review the curriculum structure.");
const gradeOptions = computed(() => document.value.grades || []);
const subjectOptions = computed(() => document.value.subjects || []);
const pathwayOptions = computed(() => document.value.pathways || []);
const trackOptions = computed(() => document.value.tracks || []);
const levelOptions = computed(() => document.value.levels || []);
const learningAreaOptions = computed(() => document.value.learning_areas || []);

function blankItem(type) {
  const defaults = {
    levels: { code: "", name: "", sequence_no: 0 },
    grades: { code: "", name: "", education_level_code: "", sequence_no: 0 },
    learning_areas: { code: "", name: "", description: "", sequence_no: 0 },
    subjects: { code: "", name: "", learning_area_code: "", subject_type: "core", description: "", sequence_no: 0 },
    offerings: { grade_code: "", subject_code: "", pathway_code: null, track_code: null, requirement_type: "required", weekly_periods: null },
    pathways: { code: "", name: "", description: "", sequence_no: 0 },
    tracks: { pathway_code: "", code: "", name: "", description: "", sequence_no: 0 },
    combinations: { code: "", name: "", grade_code: null, pathway_code: null, track_code: null, description: "", subjects: [] },
  };
  return structuredClone(defaults[type]);
}

function addItem(type) {
  if (!isDraft.value) return;
  document.value[type].push(blankItem(type));
}

function removeItem(type, index) {
  if (!isDraft.value || !window.confirm("Remove this item from the draft?")) return;
  document.value[type].splice(index, 1);
}

function subjectNames(codes = []) {
  return codes.map((code) => subjectOptions.value.find((subject) => subject.code === code)?.name || code).join(", ");
}

function valueText(value) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    templates.value = await curriculum.platform.list();
    if (selected.value) {
      const exists = templates.value.some((item) => item.id === selected.value.id);
      if (!exists) selected.value = null;
    }
    if (!selected.value && templates.value.length) await open(templates.value[0].id);
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    loading.value = false;
  }
}

async function open(id) {
  error.value = "";
  notice.value = "";
  try {
    selected.value = await curriculum.platform.get(id);
    form.value = {
      name: selected.value.name || "",
      description: selected.value.description || "",
      country_code: selected.value.country_code || "",
      framework_code: selected.value.framework_code || "",
      effective_from: selected.value.effective_from || "",
      effective_to: selected.value.effective_to || "",
    };
    document.value = structuredClone(selected.value.document || emptyDocument());
    activeSection.value = "overview";
  } catch (e) {
    error.value = getApiError(e);
  }
}

async function save() {
  if (!selected.value || !isDraft.value) return;
  saving.value = true;
  error.value = "";
  notice.value = "";
  try {
    selected.value = await curriculum.platform.update(selected.value.id, {
      ...form.value,
      document: document.value,
    });
    document.value = structuredClone(selected.value.document || emptyDocument());
    notice.value = "Draft saved successfully.";
    await load();
    if (selected.value) await open(selected.value.id);
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    saving.value = false;
  }
}

async function clone() {
  if (!selected.value) return;
  saving.value = true;
  error.value = "";
  notice.value = "";
  try {
    const copy = await curriculum.platform.clone(selected.value.id);
    await load();
    await open(copy.id);
    notice.value = "New draft version created. You can now edit it using the structured forms below.";
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    saving.value = false;
  }
}

async function publish() {
  if (!selected.value || !isDraft.value) return;
  saving.value = true;
  error.value = "";
  notice.value = "";
  try {
    selected.value = await curriculum.platform.publish(selected.value.id);
    document.value = structuredClone(selected.value.document || emptyDocument());
    notice.value = "Curriculum version published and locked.";
    await load();
    if (selected.value) await open(selected.value.id);
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    saving.value = false;
  }
}

async function archive() {
  if (!selected.value || saving.value) return;
  saving.value = true;
  error.value = "";
  notice.value = "";
  try {
    await curriculum.platform.archive(selected.value.id);
    notice.value = "Template archived.";
    selected.value = null;
    activeSection.value = "overview";
    await load();
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    saving.value = false;
  }
}

function setSection(section) {
  activeSection.value = section;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

onMounted(load);
</script>

<template>
  <div class="page-wrap curriculum-page">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div>
        <span class="eyebrow">PLATFORM · CURRICULUM</span>
        <h1 class="h3 fw-bold mt-2 mb-1">Curriculum Management</h1>
        <p class="text-muted mb-0">Build, review and publish structured curriculum templates without editing raw JSON.</p>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-primary" @click="clone" :disabled="!selected || saving"><i class="bi bi-copy me-2"></i>New version</button>
        <button v-if="isDraft" class="btn btn-primary" @click="publish" :disabled="saving"><i class="bi bi-check2-circle me-2"></i>Publish</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger border-0 shadow-sm d-flex justify-content-between align-items-center gap-3">
      <span>{{ error }}</span>
      <button class="btn-close" type="button" aria-label="Dismiss" @click="error = ''"></button>
    </div>
    <div v-if="notice" class="alert alert-success border-0 shadow-sm">{{ notice }}</div>

    <div v-if="loading" class="text-muted py-5">Loading curriculum catalog...</div>
    <div v-else-if="!templates.length" class="card border-0 shadow-sm"><div class="card-body p-5 text-center"><i class="bi bi-journal-x fs-2 text-muted"></i><h2 class="h5 mt-3">No curriculum templates</h2><p class="text-muted mb-0">Create a curriculum version to begin building the platform catalog.</p></div></div>
    <div v-else class="row g-4">
      <div class="col-xl-3">
        <div class="card border-0 shadow-sm overflow-hidden sticky-xl-top curriculum-sidebar">
          <div class="card-body p-3 border-bottom">
            <div class="d-flex justify-content-between align-items-center"><strong>Templates</strong><span class="badge text-bg-light border">{{ templates.length }}</span></div>
            <div class="small text-muted mt-1">Central platform curriculum catalog</div>
          </div>
          <div class="list-group list-group-flush template-list">
            <button v-for="item in templates" :key="item.id" class="list-group-item list-group-item-action p-3 text-start" :class="{ active: selected?.id === item.id }" type="button" @click="open(item.id)">
              <div class="d-flex justify-content-between gap-2 align-items-start"><strong>{{ item.name }}</strong><span class="badge" :class="item.status === 'published' ? 'text-bg-success' : 'text-bg-warning'">{{ item.status }}</span></div>
              <div class="small opacity-75 mt-1">{{ item.code }} · v{{ item.version_no }}</div>
              <div class="small mt-2">{{ item.counts.grades }} grades · {{ item.counts.subjects }} subjects</div>
            </button>
          </div>
        </div>
      </div>

      <div class="col-xl-9" v-if="selected">
        <div class="card border-0 shadow-sm mb-3">
          <div class="card-body p-4">
            <div class="d-flex flex-wrap justify-content-between gap-3">
              <div>
                <span class="eyebrow">{{ selected.code }} · VERSION {{ selected.version_no }}</span>
                <h2 class="h5 fw-bold mt-2 mb-1">{{ selected.name }}</h2>
                <p class="text-muted mb-0">{{ isDraft ? 'Draft version — changes can be saved before publication.' : 'Published versions are immutable. Browse every section below or create a new version to make changes.' }}</p>
              </div>
              <button v-if="selected.status === 'published' && !selected.is_default" class="btn btn-outline-danger btn-sm align-self-start" @click="archive" :disabled="saving">Archive</button>
            </div>
            <div class="row g-2 mt-4">
              <div v-for="item in [['levels','Levels'],['grades','Grades'],['learning_areas','Learning areas'],['subjects','Subjects'],['offerings','Offerings'],['pathways','Pathways'],['tracks','Tracks'],['combinations','Combinations']]" :key="item[0]" class="col-6 col-md-3">
                <button class="count-card w-100 text-start" type="button" @click="setSection(item[0])">
                  <span>{{ item[1] }}</span><strong>{{ counts[item[0]] || 0 }}</strong><i class="bi bi-arrow-right"></i>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="curriculum-tabs mb-3" role="tablist" aria-label="Curriculum sections">
          <button class="tab-button" :class="{ active: activeSection === 'overview' }" type="button" @click="setSection('overview')"><i class="bi bi-grid me-2"></i>Overview</button>
          <button v-for="section in sections" :key="section[0]" class="tab-button" :class="{ active: activeSection === section[0] }" type="button" @click="setSection(section[0])"><i class="bi bi-list-ul me-2"></i>{{ section[1] }}</button>
        </div>

        <fieldset v-if="isDraft" :disabled="saving" class="m-0 p-0 border-0">
          <div class="card border-0 shadow-sm mb-3">
            <div class="card-body p-4">
              <div class="section-title mb-3"><div><span class="eyebrow">TEMPLATE</span><h2 class="h5 fw-bold mt-2 mb-0">Template details</h2></div><span class="badge text-bg-warning">draft</span></div>
              <div class="row g-3">
                <div class="col-md-6"><label class="form-label">Template name</label><input v-model="form.name" class="form-control"></div>
                <div class="col-md-3"><label class="form-label">Country</label><input v-model="form.country_code" class="form-control" placeholder="KE"></div>
                <div class="col-md-3"><label class="form-label">Framework code</label><input v-model="form.framework_code" class="form-control" placeholder="kenya_cbc"></div>
                <div class="col-12"><label class="form-label">Description</label><textarea v-model="form.description" rows="2" class="form-control"></textarea></div>
                <div class="col-md-6"><label class="form-label">Effective from</label><input v-model="form.effective_from" type="date" class="form-control"></div>
                <div class="col-md-6"><label class="form-label">Effective to</label><input v-model="form.effective_to" type="date" class="form-control"></div>
              </div>
              <div class="d-flex justify-content-end mt-3"><button class="btn btn-primary" type="button" @click="save" :disabled="saving"><i class="bi bi-save me-2"></i>Save draft</button></div>
            </div>
          </div>
        </fieldset>

        <div v-else class="card border-0 shadow-sm mb-3">
          <div class="card-body p-4">
            <div class="section-title mb-3"><div><span class="eyebrow">TEMPLATE</span><h2 class="h5 fw-bold mt-2 mb-0">Template details</h2></div><span class="badge text-bg-success">published</span></div>
            <div class="row g-3">
              <div class="col-md-6"><label class="form-label text-muted">Template name</label><div class="readonly-value">{{ valueText(form.name) }}</div></div>
              <div class="col-md-3"><label class="form-label text-muted">Country</label><div class="readonly-value">{{ valueText(form.country_code) }}</div></div>
              <div class="col-md-3"><label class="form-label text-muted">Framework code</label><div class="readonly-value">{{ valueText(form.framework_code) }}</div></div>
              <div class="col-12"><label class="form-label text-muted">Description</label><div class="readonly-value">{{ valueText(form.description) }}</div></div>
              <div class="col-md-6"><label class="form-label text-muted">Effective from</label><div class="readonly-value">{{ valueText(form.effective_from) }}</div></div>
              <div class="col-md-6"><label class="form-label text-muted">Effective to</label><div class="readonly-value">{{ valueText(form.effective_to) }}</div></div>
            </div>
          </div>
        </div>

        <div v-if="activeSection === 'overview'" class="card border-0 shadow-sm">
          <div class="card-body p-4">
            <span class="eyebrow">STRUCTURED CATALOG</span>
            <h2 class="h5 fw-bold mt-2">How this curriculum fits together</h2>
            <p class="text-muted">{{ isDraft ? 'Use the sections above to manage the curriculum as structured records.' : 'Use the sections above to inspect the published curriculum as structured records. Published data is read-only.' }}</p>
            <div class="flow-grid">
              <button v-for="item in sections" :key="item[0]" class="flow-card text-start border-0" type="button" @click="setSection(item[0])"><div class="flow-icon"><i class="bi bi-diagram-3"></i></div><div><strong>{{ item[1] }}</strong><p>{{ item[2] }}</p></div><span>{{ document[item[0]].length }}</span></button>
            </div>
            <div class="alert alert-light border mt-4 mb-0"><i class="bi bi-info-circle me-2"></i><span v-if="isDraft">Save the draft when you are ready, then publish it to make the version immutable.</span><span v-else>Published versions remain read-only. Use <strong>New version</strong> to clone this curriculum into an editable draft.</span></div>
          </div>
        </div>

        <div v-else class="card border-0 shadow-sm">
          <div class="card-body p-4">
            <div class="section-title mb-4">
              <div><span class="eyebrow">CURRICULUM SECTION</span><h2 class="h5 fw-bold mt-2 mb-1">{{ sectionTitle }}</h2><p class="text-muted small mb-0">{{ sectionDescription }}</p></div>
              <button v-if="isDraft" class="btn btn-primary btn-sm" type="button" @click="addItem(activeSection)"><i class="bi bi-plus-lg me-1"></i>Add {{ sectionTitle.replace('Subject offerings', 'offering').replace('Subject combinations', 'combination').replace('Education levels', 'level').replace('Learning areas', 'learning area').replace('Pathways', 'pathway').replace('Tracks', 'track').replace('Grades', 'grade').replace('Subjects', 'subject') }}</button>
            </div>

            <div v-if="!document[activeSection].length" class="empty-section"><i class="bi bi-inbox"></i><h3 class="h6 fw-bold">No {{ sectionTitle.toLowerCase() }} yet</h3><p class="text-muted small mb-3">{{ isDraft ? 'Add the first item to start building this part of the curriculum.' : 'This published version does not contain any records in this section.' }}</p><button v-if="isDraft" class="btn btn-outline-primary btn-sm" type="button" @click="addItem(activeSection)"><i class="bi bi-plus-lg me-1"></i>Add item</button></div>

            <div v-else class="item-stack">
              <div v-for="(item, index) in document[activeSection]" :key="index" class="editor-item">
                <div class="item-heading"><div><span class="item-number">{{ index + 1 }}</span><strong>{{ item.name || item.code || `Item ${index + 1}` }}</strong></div><button v-if="isDraft" class="btn btn-sm btn-outline-danger" type="button" @click="removeItem(activeSection, index)"><i class="bi bi-trash"></i><span class="d-none d-sm-inline ms-1">Remove</span></button></div>

                <template v-if="activeSection === 'levels'">
                  <div class="row g-3"><div class="col-md-5"><label class="form-label">Code</label><input v-model="item.code" class="form-control" :disabled="!isDraft"></div><div class="col-md-5"><label class="form-label">Name</label><input v-model="item.name" class="form-control" :disabled="!isDraft"></div><div class="col-md-2"><label class="form-label">Sequence</label><input v-model.number="item.sequence_no" type="number" class="form-control" :disabled="!isDraft"></div></div>
                </template>
                <template v-else-if="activeSection === 'grades'">
                  <div class="row g-3"><div class="col-md-4"><label class="form-label">Code</label><input v-model="item.code" class="form-control" :disabled="!isDraft"></div><div class="col-md-4"><label class="form-label">Name</label><input v-model="item.name" class="form-control" :disabled="!isDraft"></div><div class="col-md-4"><label class="form-label">Education level</label><select v-model="item.education_level_code" class="form-select" :disabled="!isDraft"><option value="">Select level</option><option v-for="option in levelOptions" :key="option.code" :value="option.code">{{ option.name }} ({{ option.code }})</option></select></div><div class="col-md-2"><label class="form-label">Sequence</label><input v-model.number="item.sequence_no" type="number" class="form-control" :disabled="!isDraft"></div></div>
                </template>
                <template v-else-if="activeSection === 'learning_areas'">
                  <div class="row g-3"><div class="col-md-4"><label class="form-label">Code</label><input v-model="item.code" class="form-control" :disabled="!isDraft"></div><div class="col-md-5"><label class="form-label">Name</label><input v-model="item.name" class="form-control" :disabled="!isDraft"></div><div class="col-md-3"><label class="form-label">Sequence</label><input v-model.number="item.sequence_no" type="number" class="form-control" :disabled="!isDraft"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control" :disabled="!isDraft"></textarea></div></div>
                </template>
                <template v-else-if="activeSection === 'subjects'">
                  <div class="row g-3"><div class="col-md-3"><label class="form-label">Code</label><input v-model="item.code" class="form-control" :disabled="!isDraft"></div><div class="col-md-4"><label class="form-label">Name</label><input v-model="item.name" class="form-control" :disabled="!isDraft"></div><div class="col-md-5"><label class="form-label">Learning area</label><select v-model="item.learning_area_code" class="form-select" :disabled="!isDraft"><option value="">Select learning area</option><option v-for="option in learningAreaOptions" :key="option.code" :value="option.code">{{ option.name }} ({{ option.code }})</option></select></div><div class="col-md-3"><label class="form-label">Type</label><input v-model="item.subject_type" class="form-control" :disabled="!isDraft"></div><div class="col-md-3"><label class="form-label">Sequence</label><input v-model.number="item.sequence_no" type="number" class="form-control" :disabled="!isDraft"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control" :disabled="!isDraft"></textarea></div></div>
                </template>
                <template v-else-if="activeSection === 'offerings'">
                  <div class="row g-3"><div class="col-md-3"><label class="form-label">Grade</label><select v-model="item.grade_code" class="form-select" :disabled="!isDraft"><option value="">Select grade</option><option v-for="option in gradeOptions" :key="option.code" :value="option.code">{{ option.name }} ({{ option.code }})</option></select></div><div class="col-md-3"><label class="form-label">Subject</label><select v-model="item.subject_code" class="form-select" :disabled="!isDraft"><option value="">Select subject</option><option v-for="option in subjectOptions" :key="option.code" :value="option.code">{{ option.name }} ({{ option.code }})</option></select></div><div class="col-md-3"><label class="form-label">Pathway</label><select v-model="item.pathway_code" class="form-select" :disabled="!isDraft"><option :value="null">Any</option><option v-for="option in pathwayOptions" :key="option.code" :value="option.code">{{ option.name }}</option></select></div><div class="col-md-3"><label class="form-label">Track</label><select v-model="item.track_code" class="form-select" :disabled="!isDraft"><option :value="null">Any</option><option v-for="option in trackOptions" :key="option.code" :value="option.code">{{ option.name }}</option></select></div><div class="col-md-4"><label class="form-label">Requirement</label><input v-model="item.requirement_type" class="form-control" :disabled="!isDraft"></div><div class="col-md-4"><label class="form-label">Weekly periods</label><input v-model.number="item.weekly_periods" type="number" min="0" max="100" step="0.5" class="form-control" :disabled="!isDraft"></div></div>
                </template>
                <template v-else-if="activeSection === 'pathways'">
                  <div class="row g-3"><div class="col-md-4"><label class="form-label">Code</label><input v-model="item.code" class="form-control" :disabled="!isDraft"></div><div class="col-md-5"><label class="form-label">Name</label><input v-model="item.name" class="form-control" :disabled="!isDraft"></div><div class="col-md-3"><label class="form-label">Sequence</label><input v-model.number="item.sequence_no" type="number" class="form-control" :disabled="!isDraft"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control" :disabled="!isDraft"></textarea></div></div>
                </template>
                <template v-else-if="activeSection === 'tracks'">
                  <div class="row g-3"><div class="col-md-4"><label class="form-label">Pathway</label><select v-model="item.pathway_code" class="form-select" :disabled="!isDraft"><option value="">Select pathway</option><option v-for="option in pathwayOptions" :key="option.code" :value="option.code">{{ option.name }} ({{ option.code }})</option></select></div><div class="col-md-3"><label class="form-label">Code</label><input v-model="item.code" class="form-control" :disabled="!isDraft"></div><div class="col-md-3"><label class="form-label">Name</label><input v-model="item.name" class="form-control" :disabled="!isDraft"></div><div class="col-md-2"><label class="form-label">Sequence</label><input v-model.number="item.sequence_no" type="number" class="form-control" :disabled="!isDraft"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control" :disabled="!isDraft"></textarea></div></div>
                </template>
                <template v-else-if="activeSection === 'combinations'">
                  <div class="row g-3"><div class="col-md-3"><label class="form-label">Code</label><input v-model="item.code" class="form-control" :disabled="!isDraft"></div><div class="col-md-4"><label class="form-label">Name</label><input v-model="item.name" class="form-control" :disabled="!isDraft"></div><div class="col-md-5"><label class="form-label">Grade</label><select v-model="item.grade_code" class="form-select" :disabled="!isDraft"><option :value="null">Any</option><option v-for="option in gradeOptions" :key="option.code" :value="option.code">{{ option.name }}</option></select></div><div class="col-md-4"><label class="form-label">Pathway</label><select v-model="item.pathway_code" class="form-select" :disabled="!isDraft"><option :value="null">Any</option><option v-for="option in pathwayOptions" :key="option.code" :value="option.code">{{ option.name }}</option></select></div><div class="col-md-4"><label class="form-label">Track</label><select v-model="item.track_code" class="form-select" :disabled="!isDraft"><option :value="null">Any</option><option v-for="option in trackOptions" :key="option.code" :value="option.code">{{ option.name }}</option></select></div><div class="col-md-4"><label class="form-label">Subjects</label><select v-model="item.subjects" class="form-select" multiple :disabled="!isDraft"><option v-for="option in subjectOptions" :key="option.code" :value="option.code">{{ option.name }} ({{ option.code }})</option></select></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control" :disabled="!isDraft"></textarea></div></div>
                  <div v-if="!isDraft" class="small text-muted mt-3"><strong>Subjects:</strong> {{ subjectNames(item.subjects) || "—" }}</div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
