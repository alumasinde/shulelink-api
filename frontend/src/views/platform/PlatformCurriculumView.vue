<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { curriculum } from "../../api/curriculum";
import { getApiError } from "../../api/client";

const router = useRouter();
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
const sectionMeta = computed(() => sections.find(([key]) => key === activeSection.value));
const sectionTitle = computed(() => sectionMeta.value?.[1] || "Overview");
const sectionDescription = computed(() => sectionMeta.value?.[2] || "Review the curriculum structure.");
const gradeOptions = computed(() => document.value.grades || []);
const subjectOptions = computed(() => document.value.subjects || []);
const pathwayOptions = computed(() => document.value.pathways || []);
const trackOptions = computed(() => document.value.tracks || []);
const levelOptions = computed(() => document.value.levels || []);
const learningAreaOptions = computed(() => document.value.learning_areas || []);

const fieldDefs = {
  levels: [
    { key: "code", label: "Code", type: "text", col: 5 }, { key: "name", label: "Name", type: "text", col: 5 }, { key: "sequence_no", label: "Order", type: "number", col: 2 },
  ],
  grades: [
    { key: "code", label: "Code", type: "text", col: 3 }, { key: "name", label: "Name", type: "text", col: 4 }, { key: "education_level_code", label: "Education level", type: "level", col: 3 }, { key: "sequence_no", label: "Order", type: "number", col: 2 },
  ],
  learning_areas: [
    { key: "code", label: "Code", type: "text", col: 3 }, { key: "name", label: "Name", type: "text", col: 5 }, { key: "sequence_no", label: "Order", type: "number", col: 2 }, { key: "description", label: "Description", type: "textarea", col: 12 },
  ],
  subjects: [
    { key: "code", label: "Code", type: "text", col: 3 }, { key: "name", label: "Name", type: "text", col: 4 }, { key: "learning_area_code", label: "Learning area", type: "area", col: 3 }, { key: "subject_type", label: "Type", type: "subject_type", col: 2 }, { key: "sequence_no", label: "Order", type: "number", col: 2 }, { key: "description", label: "Description", type: "textarea", col: 10 },
  ],
  offerings: [
    { key: "grade_code", label: "Grade", type: "grade", col: 3 }, { key: "subject_code", label: "Subject", type: "subject", col: 3 }, { key: "pathway_code", label: "Pathway", type: "pathway_nullable", col: 2 }, { key: "track_code", label: "Track", type: "track_nullable", col: 2 }, { key: "requirement_type", label: "Requirement", type: "requirement", col: 2 }, { key: "weekly_periods", label: "Weekly periods", type: "number", col: 3 },
  ],
  pathways: [
    { key: "code", label: "Code", type: "text", col: 3 }, { key: "name", label: "Name", type: "text", col: 5 }, { key: "sequence_no", label: "Order", type: "number", col: 2 }, { key: "description", label: "Description", type: "textarea", col: 12 },
  ],
  tracks: [
    { key: "pathway_code", label: "Pathway", type: "pathway", col: 3 }, { key: "code", label: "Track code", type: "text", col: 3 }, { key: "name", label: "Name", type: "text", col: 4 }, { key: "sequence_no", label: "Order", type: "number", col: 2 }, { key: "description", label: "Description", type: "textarea", col: 12 },
  ],
  combinations: [
    { key: "code", label: "Code", type: "text", col: 3 }, { key: "name", label: "Name", type: "text", col: 5 }, { key: "grade_code", label: "Grade", type: "grade_nullable", col: 4 }, { key: "pathway_code", label: "Pathway", type: "pathway_nullable", col: 4 }, { key: "track_code", label: "Track", type: "track_nullable", col: 4 }, { key: "subjects", label: "Selected subjects", type: "subjects", col: 4 }, { key: "description", label: "Description", type: "textarea", col: 8 },
  ],
};

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
  return JSON.parse(JSON.stringify(defaults[type]));
}

function normalizeDocument(source) {
  const base = emptyDocument();
  if (!source || typeof source !== "object") return base;
  for (const key of Object.keys(base)) {
    base[key] = Array.isArray(source[key]) ? source[key].map((item) => ({ ...item, ...(Array.isArray(item?.subjects) ? { subjects: [...item.subjects] } : {}) })) : [];
  }
  return base;
}

function normalizeForm(template) {
  return {
    name: template?.name || "", description: template?.description || "", country_code: template?.country_code || "", framework_code: template?.framework_code || "",
    effective_from: String(template?.effective_from || "").slice(0, 10), effective_to: String(template?.effective_to || "").slice(0, 10),
  };
}

function addItem(type) {
  if (!isDraft.value || saving.value) return;
  document.value[type].push(blankItem(type));
}

function removeItem(type, index) {
  if (!isDraft.value || saving.value || !window.confirm("Remove this item from the draft?")) return;
  document.value[type].splice(index, 1);
}

function subjectNames(codes = []) {
  return codes.map((code) => subjectOptions.value.find((subject) => subject.code === code)?.name || code).join(", ");
}

function optionsFor(type) {
  return {
    level: levelOptions.value,
    area: learningAreaOptions.value,
    grade: gradeOptions.value,
    subject: subjectOptions.value,
    pathway: pathwayOptions.value,
    pathway_nullable: pathwayOptions.value,
    track_nullable: trackOptions.value,
    grade_nullable: gradeOptions.value,
  }[type] || [];
}

function optionLabel(option, type) {
  if (type === "subject" || type === "track_nullable") return `${option.name} (${option.code})`;
  return option.name ? `${option.name}${option.code ? ` (${option.code})` : ""}` : option.code;
}

function isNullable(type) {
  return ["pathway_nullable", "track_nullable", "grade_nullable"].includes(type);
}

function displayValue(item, field) {
  const value = item[field.key];
  if (field.type === "subjects") return subjectNames(value || []) || "—";
  if (field.type === "textarea") return value || "—";
  if (field.type === "number") return value === null || value === undefined || value === "" ? "—" : String(value);
  const options = optionsFor(field.type);
  const match = options.find((option) => option.code === value);
  return match ? optionLabel(match, field.type) : (value === null || value === undefined || value === "" ? "—" : String(value));
}

async function open(id) {
  error.value = "";
  notice.value = "";
  try {
    const next = await curriculum.platform.get(id);
    const nextDocument = normalizeDocument(next.document);
    const nextForm = normalizeForm(next);
    selected.value = next;
    form.value = nextForm;
    document.value = nextDocument;
    activeSection.value = "overview";
    error.value = "";
  } catch (e) {
    console.error("[ShuleLink] Failed to load curriculum template", e);
    error.value = getApiError(e, "We could not load this curriculum version. Please try again.");
  }
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const nextTemplates = await curriculum.platform.list();
    templates.value = Array.isArray(nextTemplates) ? nextTemplates : [];
    if (selected.value) {
      const exists = templates.value.some((item) => item.id === selected.value.id);
      if (!exists) selected.value = null;
    }
    if (!selected.value && templates.value.length) await open(templates.value[0].id);
  } catch (e) {
    console.error("[ShuleLink] Failed to load curriculum catalog", e);
    error.value = getApiError(e, "We could not load the curriculum catalog. Please try again.");
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!selected.value || !isDraft.value || saving.value) return;
  saving.value = true; error.value = ""; notice.value = "";
  try {
    const id = selected.value.id;
    await curriculum.platform.update(id, { ...form.value, document: document.value });
    await load();
    await open(id);
    notice.value = "Draft saved successfully.";
  } catch (e) {
    console.error("[ShuleLink] Failed to save curriculum draft", e);
    error.value = getApiError(e, "We could not save this curriculum draft. Please try again.");
  } finally { saving.value = false; }
}

async function clone() {
  if (!selected.value || saving.value) return;
  saving.value = true; error.value = ""; notice.value = "";
  try {
    const copy = await curriculum.platform.clone(selected.value.id);
    await load();
    await open(copy.id);
    notice.value = "New draft version created. You can now edit it.";
  } catch (e) {
    console.error("[ShuleLink] Failed to clone curriculum version", e);
    error.value = getApiError(e, "We could not create a new curriculum version. Please try again.");
  } finally { saving.value = false; }
}

async function publish() {
  if (!selected.value || !isDraft.value || saving.value) return;
  saving.value = true; error.value = ""; notice.value = "";
  try {
    const id = selected.value.id;
    await curriculum.platform.publish(id);
    await load();
    await open(id);
    notice.value = "Curriculum version published and locked.";
  } catch (e) {
    console.error("[ShuleLink] Failed to publish curriculum version", e);
    error.value = getApiError(e, "We could not publish this curriculum version. Please try again.");
  } finally { saving.value = false; }
}

async function archive() {
  if (!selected.value || saving.value) return;
  saving.value = true; error.value = ""; notice.value = "";
  try {
    await curriculum.platform.archive(selected.value.id);
    selected.value = null;
    activeSection.value = "overview";
    await load();
    notice.value = "Template archived.";
  } catch (e) {
    console.error("[ShuleLink] Failed to archive curriculum version", e);
    error.value = getApiError(e, "We could not archive this curriculum version. Please try again.");
  } finally { saving.value = false; }
}

function setSection(section) {
  activeSection.value = section;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function backToOverview() {
  if (activeSection.value !== "overview") setSection("overview");
  else window.scrollTo({ top: 0, behavior: "smooth" });
}

onMounted(load);
</script>

<template>
  <div class="page-wrap curriculum-page">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div>
        <button class="back-link mb-3" type="button" @click="router.push('/platform')"><i class="bi bi-arrow-left me-2"></i>Back to Dashboard</button>
        <span class="eyebrow d-block">PLATFORM · CURRICULUM</span>
        <h1 class="h3 fw-bold mt-2 mb-1">Curriculum Management</h1>
        <p class="text-muted mb-0">Build, review and publish structured curriculum templates without editing raw JSON.</p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <button class="btn btn-outline-primary" type="button" @click="clone" :disabled="!selected || saving"><i class="bi bi-copy me-2"></i>New version</button>
        <button v-if="isDraft" class="btn btn-primary" type="button" @click="publish" :disabled="saving"><i class="bi bi-check2-circle me-2"></i>Publish</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger border-0 shadow-sm d-flex justify-content-between align-items-center gap-3" role="alert"><div><i class="bi bi-exclamation-triangle me-2"></i>{{ error }}</div><button class="btn-close flex-shrink-0" type="button" aria-label="Dismiss" @click="error = ''"></button></div>
    <div v-if="notice" class="alert alert-success border-0 shadow-sm d-flex justify-content-between align-items-center gap-3" role="status"><span><i class="bi bi-check-circle me-2"></i>{{ notice }}</span><button class="btn-close" type="button" aria-label="Dismiss" @click="notice = ''"></button></div>

    <div v-if="loading" class="card border-0 shadow-sm"><div class="card-body p-5 text-center text-muted"><div class="spinner-border spinner-border-sm me-2"></div>Loading curriculum catalog...</div></div>
    <div v-else-if="!templates.length" class="card border-0 shadow-sm"><div class="card-body p-5 text-center"><i class="bi bi-journal-x empty-icon"></i><h2 class="h5 mt-3">No curriculum templates</h2><p class="text-muted mb-3">Create a curriculum version to begin building the platform catalog.</p></div></div>

    <div v-else class="row g-4">
      <div class="col-xl-3">
        <div class="card border-0 shadow-sm overflow-hidden sticky-xl-top curriculum-sidebar">
          <div class="card-body p-3 border-bottom"><div class="d-flex justify-content-between align-items-center"><strong>Templates</strong><span class="badge text-bg-light border">{{ templates.length }}</span></div><div class="small text-muted mt-1">Central platform curriculum catalog</div></div>
          <div class="list-group list-group-flush template-list">
            <button v-for="item in templates" :key="item.id" class="list-group-item list-group-item-action p-3 text-start" :class="{ active: selected?.id === item.id }" type="button" @click="open(item.id)">
              <div class="d-flex justify-content-between gap-2 align-items-start"><strong>{{ item.name }}</strong><span class="badge" :class="item.status === 'published' ? 'text-bg-success' : 'text-bg-warning'">{{ item.status }}</span></div><div class="small opacity-75 mt-1">{{ item.code }} · v{{ item.version_no }}</div><div class="small mt-2">{{ item.counts.grades }} grades · {{ item.counts.subjects }} subjects</div>
            </button>
          </div>
        </div>
      </div>

      <div class="col-xl-9" v-if="selected">
        <div class="card border-0 shadow-sm mb-3 hero-card">
          <div class="card-body p-4">
            <div class="d-flex flex-wrap justify-content-between gap-3"><div><span class="eyebrow">{{ selected.code }} · VERSION {{ selected.version_no }}</span><h2 class="h5 fw-bold mt-2 mb-1">{{ selected.name }}</h2><p class="text-muted mb-0">{{ isDraft ? 'Draft version — changes can be saved before publication.' : 'Published versions are immutable. Browse every section or create a new version to make changes.' }}</p></div><button v-if="selected.status === 'published' && !selected.is_default" class="btn btn-outline-danger btn-sm align-self-start" type="button" @click="archive" :disabled="saving"><i class="bi bi-archive me-1"></i>Archive</button></div>
            <div class="row g-2 mt-4"><div v-for="item in [['levels','Levels'],['grades','Grades'],['learning_areas','Learning areas'],['subjects','Subjects'],['offerings','Offerings'],['pathways','Pathways'],['tracks','Tracks'],['combinations','Combinations']]" :key="item[0]" class="col-6 col-md-3"><button class="count-card w-100 text-start" type="button" @click="setSection(item[0])"><span>{{ item[1] }}</span><strong>{{ counts[item[0]] || 0 }}</strong><i class="bi bi-arrow-right"></i></button></div></div>
          </div>
        </div>

        <div class="curriculum-tabs mb-3" role="tablist" aria-label="Curriculum sections"><button class="tab-button" :class="{ active: activeSection === 'overview' }" type="button" @click="setSection('overview')"><i class="bi bi-grid me-2"></i>Overview</button><button v-for="section in sections" :key="section[0]" class="tab-button" :class="{ active: activeSection === section[0] }" type="button" @click="setSection(section[0])"><i class="bi bi-list-ul me-2"></i>{{ section[1] }}</button></div>
        <div v-if="activeSection !== 'overview'" class="d-flex justify-content-between align-items-center mb-3 section-backbar"><button class="back-link" type="button" @click="backToOverview"><i class="bi bi-arrow-left me-2"></i>Back to overview</button><span class="small text-muted">{{ sectionTitle }}</span></div>

        <div v-if="isDraft" class="card border-0 shadow-sm mb-3"><div class="card-body p-4"><div class="section-title mb-3"><div><span class="eyebrow">TEMPLATE</span><h2 class="h5 fw-bold mt-2 mb-0">Template details</h2></div><span class="badge text-bg-warning">draft</span></div><div class="row g-3"><div class="col-md-6"><label class="form-label">Template name</label><input v-model="form.name" class="form-control"></div><div class="col-md-3"><label class="form-label">Country</label><input v-model="form.country_code" class="form-control" placeholder="KE"></div><div class="col-md-3"><label class="form-label">Framework code</label><input v-model="form.framework_code" class="form-control" placeholder="kenya_cbc"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="form.description" rows="2" class="form-control"></textarea></div><div class="col-md-6"><label class="form-label">Effective from</label><input v-model="form.effective_from" type="date" class="form-control"></div><div class="col-md-6"><label class="form-label">Effective to</label><input v-model="form.effective_to" type="date" class="form-control"></div></div></div></div>
        <div v-else class="card border-0 shadow-sm mb-3"><div class="card-body p-4"><div class="section-title mb-3"><div><span class="eyebrow">TEMPLATE</span><h2 class="h5 fw-bold mt-2 mb-0">Template details</h2></div><span class="badge text-bg-success">published</span></div><div class="row g-3"><div class="col-md-6"><label class="form-label text-muted">Template name</label><div class="readonly-value">{{ form.name || '—' }}</div></div><div class="col-md-3"><label class="form-label text-muted">Country</label><div class="readonly-value">{{ form.country_code || '—' }}</div></div><div class="col-md-3"><label class="form-label text-muted">Framework code</label><div class="readonly-value">{{ form.framework_code || '—' }}</div></div><div class="col-12"><label class="form-label text-muted">Description</label><div class="readonly-value">{{ form.description || '—' }}</div></div><div class="col-md-6"><label class="form-label text-muted">Effective from</label><div class="readonly-value">{{ form.effective_from || '—' }}</div></div><div class="col-md-6"><label class="form-label text-muted">Effective to</label><div class="readonly-value">{{ form.effective_to || '—' }}</div></div></div></div></div>

        <div v-if="activeSection === 'overview'" class="card border-0 shadow-sm"><div class="card-body p-4"><div class="d-flex justify-content-between align-items-start gap-3 mb-3"><div><span class="eyebrow">STRUCTURED CATALOG</span><h2 class="h5 fw-bold mt-2 mb-1">How this curriculum fits together</h2><p class="text-muted mb-0">{{ isDraft ? 'Use the sections above to manage the curriculum as structured records.' : 'Inspect the published curriculum as structured records. Published data is read-only.' }}</p></div><span class="catalog-status" :class="isDraft ? 'draft' : 'published'">{{ selected.status }}</span></div><div class="flow-grid"><button v-for="item in sections" :key="item[0]" class="flow-card text-start" type="button" @click="setSection(item[0])"><div class="flow-icon"><i class="bi bi-diagram-3"></i></div><div><strong>{{ item[1] }}</strong><p>{{ item[2] }}</p></div><span>{{ document[item[0]].length }}</span></button></div><div class="alert alert-light border mt-4 mb-0"><i class="bi bi-info-circle me-2"></i><span v-if="isDraft">Save the draft when ready, then publish it to make the version immutable.</span><span v-else>Published versions remain read-only. Use <strong>New version</strong> to clone this curriculum into an editable draft.</span></div></div></div>

        <div v-else class="card border-0 shadow-sm"><div class="card-body p-4"><div class="section-title mb-4"><div><span class="eyebrow">CURRICULUM SECTION</span><h2 class="h5 fw-bold mt-2 mb-1">{{ sectionTitle }}</h2><p class="text-muted small mb-0">{{ sectionDescription }}</p></div><button v-if="isDraft" class="btn btn-primary btn-sm" type="button" @click="addItem(activeSection)"><i class="bi bi-plus-lg me-1"></i>Add {{ sectionTitle.replace('Subject offerings','offering').replace('Subject combinations','combination').replace('Education levels','level').replace('Learning areas','learning area').replace('Pathways','pathway').replace('Tracks','track').replace('Grades','grade').replace('Subjects','subject') }}</button></div><div v-if="!document[activeSection].length" class="empty-section"><i class="bi bi-inbox"></i><h3 class="h6 fw-bold">No {{ sectionTitle.toLowerCase() }} yet</h3><p class="text-muted small mb-3">{{ isDraft ? 'Add the first item to start building this part of the curriculum.' : 'This published version does not contain any records in this section.' }}</p><button v-if="isDraft" class="btn btn-outline-primary btn-sm" type="button" @click="addItem(activeSection)"><i class="bi bi-plus-lg me-1"></i>Add item</button></div><div v-else class="item-stack"><div v-for="(item,index) in document[activeSection]" :key="index" class="editor-item"><div class="item-heading"><div><span class="item-number">{{ index + 1 }}</span><strong>{{ item.name || item.code || `Item ${index + 1}` }}</strong></div><button v-if="isDraft" class="btn btn-sm btn-outline-danger" type="button" @click="removeItem(activeSection,index)"><i class="bi bi-trash"></i><span class="d-none d-sm-inline ms-1">Remove</span></button></div><div class="row g-3"><div v-for="field in fieldDefs[activeSection]" :key="field.key" :class="`col-md-${field.col || 12}`"><label class="form-label">{{ field.label }}</label><div v-if="!isDraft" class="readonly-value">{{ displayValue(item, field) }}</div><template v-else><textarea v-if="field.type === 'textarea'" v-model="item[field.key]" rows="3" class="form-control"></textarea><select v-else-if="field.type === 'subjects'" v-model="item[field.key]" class="form-select" multiple size="5"><option v-for="option in subjectOptions" :key="option.code" :value="option.code">{{ option.name }} ({{ option.code }})</option></select><select v-else-if="['level','area','grade','subject','pathway','pathway_nullable','track_nullable','grade_nullable'].includes(field.type)" v-model="item[field.key]" class="form-select"><option v-if="isNullable(field.type)" :value="null">Any</option><option v-else-if="field.type === 'level' || field.type === 'area' || field.type === 'grade' || field.type === 'subject' || field.type === 'pathway'" value="">Select {{ field.label.toLowerCase() }}</option><option v-for="option in optionsFor(field.type)" :key="option.code" :value="option.code">{{ optionLabel(option,field.type) }}</option></select><select v-else-if="field.type === 'subject_type'" v-model="item[field.key]" class="form-select"><option value="core">Core</option><option value="elective">Elective</option><option value="optional">Optional</option></select><select v-else-if="field.type === 'requirement'" v-model="item[field.key]" class="form-select"><option value="required">Required</option><option value="elective">Elective</option><option value="optional">Optional</option></select><input v-else v-model="item[field.key]" :type="field.type === 'number' ? 'number' : 'text'" :min="field.type === 'number' ? 0 : undefined" class="form-control"></template></div></div><div v-if="isDraft && activeSection === 'combinations' && item.subjects?.length" class="selected-subjects mt-2"><span v-for="code in item.subjects" :key="code" class="badge text-bg-light border me-1 mb-1">{{ subjectNames([code]) }}</span></div><div v-if="!isDraft && activeSection === 'combinations'" class="small text-muted mt-3"><strong>Subjects:</strong> {{ subjectNames(item.subjects) || '—' }}</div></div></div></div></div>

        <div v-if="isDraft" class="save-bar mt-3"><div><strong>Draft changes</strong><div class="tiny text-muted">Save the complete template as one versioned document.</div></div><button class="btn btn-primary" type="button" @click="save" :disabled="saving"><span v-if="saving" class="spinner-border spinner-border-sm me-2"></span><i v-else class="bi bi-save me-2"></i>Save draft</button></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.curriculum-sidebar { top: 92px; }
.template-list { max-height: 70vh; overflow-y: auto; }
.template-list .list-group-item.active { background: var(--sl-primary); border-color: var(--sl-primary); color: #fff; }
.back-link { display: inline-flex; align-items: center; border: 0; background: transparent; color: var(--sl-primary); padding: 0; font-size: .78rem; font-weight: 600; text-decoration: none; }
.back-link:hover { color: #174ea6; text-decoration: underline; }
.section-backbar { padding: 8px 2px; }
.hero-card { border-top: 3px solid var(--sl-primary) !important; }
.count-card { position: relative; border: 1px solid #e8edf3; background: #f9fbfd; border-radius: 11px; padding: 12px; min-height: 75px; color: var(--sl-ink); transition: .15s ease; }
.count-card:hover { border-color: #c6d7f2; background: #f4f8ff; transform: translateY(-1px); }
.count-card span { display: block; color: #6b7280; font-size: .68rem; margin-bottom: 5px; }
.count-card strong { font-size: 1.2rem; }
.count-card i { position: absolute; right: 11px; bottom: 11px; color: #9aa4b2; }
.section-title { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.curriculum-tabs { display: flex; gap: 5px; overflow-x: auto; padding: 4px; background: #fff; border: 1px solid #e8edf3; border-radius: 12px; box-shadow: 0 3px 14px rgba(23,32,51,.03); }
.tab-button { flex: 0 0 auto; border: 0; background: transparent; color: #64748b; border-radius: 9px; padding: 9px 12px; font-size: .76rem; font-weight: 600; white-space: nowrap; }
.tab-button:hover { background: #f4f7fb; color: var(--sl-primary); }
.tab-button.active { background: #eaf1ff; color: var(--sl-primary); }
.flow-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.flow-card { width: 100%; border: 1px solid #edf1f5; border-radius: 11px; padding: 13px; display: flex; align-items: center; gap: 10px; cursor: pointer; background: #fff; }
.flow-card:hover { border-color: #cddbf2; background: #fafcff; }
.flow-icon { width: 34px; height: 34px; border-radius: 9px; background: #eef4ff; color: var(--sl-primary); display: flex; align-items: center; justify-content: center; flex: 0 0 34px; }
.flow-card strong { font-size: .8rem; }
.flow-card p { margin: 2px 0 0; color: #8a94a3; font-size: .68rem; }
.flow-card > span { margin-left: auto; font-weight: 700; font-size: .8rem; }
.catalog-status { padding: 5px 9px; border-radius: 999px; font-size: .68rem; font-weight: 700; text-transform: capitalize; }
.catalog-status.draft { background: #fff4d6; color: #946200; }
.catalog-status.published { background: #dff6e8; color: #18794e; }
.readonly-value { min-height: 38px; display: flex; align-items: center; padding: 8px 11px; border: 1px solid #edf1f5; border-radius: 8px; background: #f8fafc; color: #334155; font-size: .8rem; white-space: pre-wrap; }
.empty-icon { font-size: 2rem; color: #9aa4b2; }
.empty-section { text-align: center; padding: 55px 20px; border: 1px dashed #dce3ec; border-radius: 13px; background: #fbfcfe; }
.empty-section > i { font-size: 2rem; color: #9aa4b2; }
.empty-section h3 { margin-top: 12px; }
.item-stack { display: flex; flex-direction: column; gap: 12px; }
.editor-item { border: 1px solid #e8edf3; border-radius: 13px; padding: 16px; background: #fff; }
.item-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-bottom: 14px; margin-bottom: 15px; border-bottom: 1px solid #edf1f5; }
.item-heading > div { min-width: 0; display: flex; align-items: center; gap: 9px; }
.item-heading strong { font-size: .82rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-number { width: 25px; height: 25px; border-radius: 7px; background: #eef4ff; color: var(--sl-primary); display: inline-flex; align-items: center; justify-content: center; font-size: .68rem; font-weight: 700; flex: 0 0 25px; }
.form-label { font-size: .72rem; font-weight: 600; color: #4b5563; margin-bottom: 5px; }
.form-control, .form-select { font-size: .78rem; }
select[multiple] { min-height: 115px; }
.selected-subjects { min-height: 22px; }
.save-bar { position: sticky; bottom: 14px; z-index: 10; background: rgba(255,255,255,.96); backdrop-filter: blur(8px); border: 1px solid #dce4ee; border-radius: 13px; padding: 12px 15px; display: flex; align-items: center; justify-content: space-between; gap: 15px; box-shadow: 0 8px 28px rgba(23,32,51,.1); }
@media (max-width: 991.98px) { .curriculum-sidebar { position: static !important; } }
@media (max-width: 767.98px) { .flow-grid { grid-template-columns: 1fr; } .section-title { flex-direction: column; } .save-bar { position: static; } }
</style>
