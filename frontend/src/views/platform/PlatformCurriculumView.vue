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
  document.value[type].push(blankItem(type));
}

function removeItem(type, index) {
  if (!window.confirm("Remove this item from the draft?")) return;
  document.value[type].splice(index, 1);
}

function subjectNames(codes = []) {
  return codes.map((code) => subjectOptions.value.find((subject) => subject.code === code)?.name || code).join(", ");
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    templates.value = await curriculum.platform.list();
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
    await open(selected.value.id);
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
    notice.value = "New draft version created. You can now edit it using the forms below.";
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    saving.value = false;
  }
}

async function publish() {
  if (!selected.value) return;
  saving.value = true;
  error.value = "";
  notice.value = "";
  try {
    selected.value = await curriculum.platform.publish(selected.value.id);
    document.value = structuredClone(selected.value.document || emptyDocument());
    notice.value = "Curriculum version published and locked.";
    await load();
    await open(selected.value.id);
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    saving.value = false;
  }
}

async function archive() {
  if (!selected.value) return;
  saving.value = true;
  error.value = "";
  try {
    await curriculum.platform.archive(selected.value.id);
    notice.value = "Template archived.";
    selected.value = null;
    await load();
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    saving.value = false;
  }
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

    <div v-if="error" class="alert alert-danger border-0 shadow-sm">{{ error }}</div>
    <div v-if="notice" class="alert alert-success border-0 shadow-sm">{{ notice }}</div>

    <div v-if="loading" class="text-muted py-5">Loading curriculum catalog...</div>
    <div v-else class="row g-4">
      <div class="col-xl-3">
        <div class="card border-0 shadow-sm overflow-hidden sticky-xl-top curriculum-sidebar">
          <div class="card-body p-3 border-bottom">
            <div class="d-flex justify-content-between align-items-center"><strong>Templates</strong><span class="badge text-bg-light border">{{ templates.length }}</span></div>
            <div class="small text-muted mt-1">Central platform curriculum catalog</div>
          </div>
          <div class="list-group list-group-flush template-list">
            <button v-for="item in templates" :key="item.id" class="list-group-item list-group-item-action p-3 text-start" :class="{ active: selected?.id === item.id }" @click="open(item.id)">
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
                <p class="text-muted mb-0">{{ isDraft ? 'Draft version — changes can be saved before publication.' : 'Published versions are immutable. Create a new version to make changes.' }}</p>
              </div>
              <button v-if="selected.status === 'published' && !selected.is_default" class="btn btn-outline-danger btn-sm align-self-start" @click="archive" :disabled="saving">Archive</button>
            </div>
            <div class="row g-2 mt-4">
              <div v-for="item in [['levels','Levels'],['grades','Grades'],['learning_areas','Learning areas'],['subjects','Subjects'],['offerings','Offerings'],['pathways','Pathways'],['tracks','Tracks'],['combinations','Combinations']]" :key="item[0]" class="col-6 col-md-3">
                <button class="count-card w-100 text-start" type="button" @click="activeSection = item[0]">
                  <span>{{ item[1] }}</span><strong>{{ counts[item[0]] || 0 }}</strong><i class="bi bi-arrow-right"></i>
                </button>
              </div>
            </div>
          </div>
        </div>

        <fieldset :disabled="!isDraft || saving" class="m-0 p-0 border-0">
          <div class="card border-0 shadow-sm mb-3">
            <div class="card-body p-4">
              <div class="section-title mb-3"><div><span class="eyebrow">TEMPLATE</span><h2 class="h5 fw-bold mt-2 mb-0">Template details</h2></div><span class="badge" :class="isDraft ? 'text-bg-warning' : 'text-bg-success'">{{ selected.status }}</span></div>
              <div class="row g-3">
                <div class="col-md-6"><label class="form-label">Template name</label><input v-model="form.name" class="form-control"></div>
                <div class="col-md-3"><label class="form-label">Country</label><input v-model="form.country_code" class="form-control" placeholder="KE"></div>
                <div class="col-md-3"><label class="form-label">Framework code</label><input v-model="form.framework_code" class="form-control" placeholder="kenya_cbc"></div>
                <div class="col-12"><label class="form-label">Description</label><textarea v-model="form.description" rows="2" class="form-control"></textarea></div>
                <div class="col-md-6"><label class="form-label">Effective from</label><input v-model="form.effective_from" type="date" class="form-control"></div>
                <div class="col-md-6"><label class="form-label">Effective to</label><input v-model="form.effective_to" type="date" class="form-control"></div>
              </div>
            </div>
          </div>

          <div class="curriculum-tabs mb-3" role="tablist">
            <button class="tab-button" :class="{ active: activeSection === 'overview' }" @click="activeSection = 'overview'"><i class="bi bi-grid me-2"></i>Overview</button>
            <button v-for="section in sections" :key="section[0]" class="tab-button" :class="{ active: activeSection === section[0] }" @click="activeSection = section[0]"><i class="bi bi-list-ul me-2"></i>{{ section[1] }}</button>
          </div>

          <div v-if="activeSection === 'overview'" class="card border-0 shadow-sm">
            <div class="card-body p-4">
              <span class="eyebrow">STRUCTURED CATALOG</span>
              <h2 class="h5 fw-bold mt-2">How this curriculum fits together</h2>
              <p class="text-muted">Use the sections above to manage the curriculum as structured records. Relationships use codes from the same template, keeping the catalog portable and versionable.</p>
              <div class="flow-grid">
                <div v-for="item in sections" :key="item[0]" class="flow-card" @click="activeSection = item[0]"><div class="flow-icon"><i class="bi bi-diagram-3"></i></div><div><strong>{{ item[1] }}</strong><p>{{ item[2] }}</p></div><span>{{ document[item[0]].length }}</span></div>
              </div>
              <div class="alert alert-light border mt-4 mb-0"><i class="bi bi-info-circle me-2"></i>Published versions remain read-only. Use <strong>New version</strong> to clone a published curriculum into a draft.</div>
            </div>
          </div>

          <div v-else class="card border-0 shadow-sm">
            <div class="card-body p-4">
              <div class="section-title mb-4">
                <div><span class="eyebrow">CURRICULUM SECTION</span><h2 class="h5 fw-bold mt-2 mb-1">{{ sectionTitle }}</h2><p class="text-muted small mb-0">{{ sections.find(([key]) => key === activeSection)?.[2] }}</p></div>
                <button class="btn btn-primary btn-sm" @click="addItem(activeSection)"><i class="bi bi-plus-lg me-1"></i>Add {{ sectionTitle.replace('Subject offerings', 'offering').replace('Subject combinations', 'combination').replace('Education levels', 'level').replace('Learning areas', 'learning area').replace('Pathways', 'pathway').replace('Tracks', 'track').replace('Grades', 'grade').replace('Subjects', 'subject') }}</button>
              </div>

              <div v-if="!document[activeSection].length" class="empty-section"><i class="bi bi-inbox"></i><h3 class="h6 fw-bold">No {{ sectionTitle.toLowerCase() }} yet</h3><p class="text-muted small mb-3">Add the first item to start building this part of the curriculum.</p><button class="btn btn-outline-primary btn-sm" @click="addItem(activeSection)"><i class="bi bi-plus-lg me-1"></i>Add item</button></div>

              <div v-else class="item-stack">
                <div v-for="(item, index) in document[activeSection]" :key="index" class="editor-item">
                  <div class="item-heading"><div><span class="item-number">{{ index + 1 }}</span><strong>{{ item.name || item.code || `Item ${index + 1}` }}</strong></div><button class="btn btn-sm btn-outline-danger" type="button" @click="removeItem(activeSection, index)"><i class="bi bi-trash"></i><span class="d-none d-sm-inline ms-1">Remove</span></button></div>

                  <template v-if="activeSection === 'levels'">
                    <div class="row g-3"><div class="col-md-5"><label class="form-label">Code</label><input v-model="item.code" class="form-control" placeholder="pre_primary"></div><div class="col-md-5"><label class="form-label">Name</label><input v-model="item.name" class="form-control" placeholder="Pre-Primary"></div><div class="col-md-2"><label class="form-label">Order</label><input v-model.number="item.sequence_no" type="number" min="0" class="form-control"></div></div>
                  </template>

                  <template v-else-if="activeSection === 'grades'">
                    <div class="row g-3"><div class="col-md-3"><label class="form-label">Code</label><input v-model="item.code" class="form-control" placeholder="grade_1"></div><div class="col-md-4"><label class="form-label">Name</label><input v-model="item.name" class="form-control" placeholder="Grade 1"></div><div class="col-md-3"><label class="form-label">Education level</label><select v-model="item.education_level_code" class="form-select"><option value="">Select level</option><option v-for="level in levelOptions" :key="level.code" :value="level.code">{{ level.name }} ({{ level.code }})</option></select></div><div class="col-md-2"><label class="form-label">Order</label><input v-model.number="item.sequence_no" type="number" min="0" class="form-control"></div></div>
                  </template>

                  <template v-else-if="activeSection === 'learning_areas'">
                    <div class="row g-3"><div class="col-md-3"><label class="form-label">Code</label><input v-model="item.code" class="form-control"></div><div class="col-md-5"><label class="form-label">Name</label><input v-model="item.name" class="form-control"></div><div class="col-md-2"><label class="form-label">Order</label><input v-model.number="item.sequence_no" type="number" min="0" class="form-control"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control"></textarea></div></div>
                  </template>

                  <template v-else-if="activeSection === 'subjects'">
                    <div class="row g-3"><div class="col-md-3"><label class="form-label">Code</label><input v-model="item.code" class="form-control"></div><div class="col-md-4"><label class="form-label">Name</label><input v-model="item.name" class="form-control"></div><div class="col-md-3"><label class="form-label">Learning area</label><select v-model="item.learning_area_code" class="form-select"><option value="">Not assigned</option><option v-for="area in learningAreaOptions" :key="area.code" :value="area.code">{{ area.name }}</option></select></div><div class="col-md-2"><label class="form-label">Type</label><select v-model="item.subject_type" class="form-select"><option value="core">Core</option><option value="elective">Elective</option><option value="optional">Optional</option></select></div><div class="col-md-2"><label class="form-label">Order</label><input v-model.number="item.sequence_no" type="number" min="0" class="form-control"></div><div class="col-md-10"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control"></textarea></div></div>
                  </template>

                  <template v-else-if="activeSection === 'offerings'">
                    <div class="row g-3"><div class="col-md-3"><label class="form-label">Grade</label><select v-model="item.grade_code" class="form-select"><option value="">Select grade</option><option v-for="grade in gradeOptions" :key="grade.code" :value="grade.code">{{ grade.name }}</option></select></div><div class="col-md-3"><label class="form-label">Subject</label><select v-model="item.subject_code" class="form-select"><option value="">Select subject</option><option v-for="subject in subjectOptions" :key="subject.code" :value="subject.code">{{ subject.name }}</option></select></div><div class="col-md-2"><label class="form-label">Pathway</label><select v-model="item.pathway_code" class="form-select"><option :value="null">Any</option><option v-for="pathway in pathwayOptions" :key="pathway.code" :value="pathway.code">{{ pathway.name }}</option></select></div><div class="col-md-2"><label class="form-label">Track</label><select v-model="item.track_code" class="form-select"><option :value="null">Any</option><option v-for="track in trackOptions" :key="`${track.pathway_code}-${track.code}`" :value="track.code">{{ track.name }}</option></select></div><div class="col-md-2"><label class="form-label">Requirement</label><select v-model="item.requirement_type" class="form-select"><option value="required">Required</option><option value="elective">Elective</option><option value="optional">Optional</option></select></div><div class="col-md-3"><label class="form-label">Weekly periods</label><input v-model.number="item.weekly_periods" type="number" min="0" max="100" step="0.5" class="form-control" placeholder="e.g. 5"></div></div>
                  </template>

                  <template v-else-if="activeSection === 'pathways'">
                    <div class="row g-3"><div class="col-md-3"><label class="form-label">Code</label><input v-model="item.code" class="form-control"></div><div class="col-md-5"><label class="form-label">Name</label><input v-model="item.name" class="form-control"></div><div class="col-md-2"><label class="form-label">Order</label><input v-model.number="item.sequence_no" type="number" min="0" class="form-control"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control"></textarea></div></div>
                  </template>

                  <template v-else-if="activeSection === 'tracks'">
                    <div class="row g-3"><div class="col-md-3"><label class="form-label">Pathway</label><select v-model="item.pathway_code" class="form-select"><option value="">Select pathway</option><option v-for="pathway in pathwayOptions" :key="pathway.code" :value="pathway.code">{{ pathway.name }}</option></select></div><div class="col-md-3"><label class="form-label">Track code</label><input v-model="item.code" class="form-control"></div><div class="col-md-4"><label class="form-label">Name</label><input v-model="item.name" class="form-control"></div><div class="col-md-2"><label class="form-label">Order</label><input v-model.number="item.sequence_no" type="number" min="0" class="form-control"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="item.description" rows="2" class="form-control"></textarea></div></div>
                  </template>

                  <template v-else-if="activeSection === 'combinations'">
                    <div class="row g-3"><div class="col-md-3"><label class="form-label">Code</label><input v-model="item.code" class="form-control"></div><div class="col-md-5"><label class="form-label">Name</label><input v-model="item.name" class="form-control"></div><div class="col-md-4"><label class="form-label">Grade</label><select v-model="item.grade_code" class="form-select"><option :value="null">Any grade</option><option v-for="grade in gradeOptions" :key="grade.code" :value="grade.code">{{ grade.name }}</option></select></div><div class="col-md-4"><label class="form-label">Pathway</label><select v-model="item.pathway_code" class="form-select"><option :value="null">Any pathway</option><option v-for="pathway in pathwayOptions" :key="pathway.code" :value="pathway.code">{{ pathway.name }}</option></select></div><div class="col-md-4"><label class="form-label">Track</label><select v-model="item.track_code" class="form-select"><option :value="null">Any track</option><option v-for="track in trackOptions" :key="`${track.pathway_code}-${track.code}`" :value="track.code">{{ track.name }}</option></select></div><div class="col-md-4"><label class="form-label">Selected subjects</label><select v-model="item.subjects" class="form-select" multiple size="4"><option v-for="subject in subjectOptions" :key="subject.code" :value="subject.code">{{ subject.name }}</option></select><div class="form-text">Hold Ctrl/Cmd to select multiple subjects.</div></div><div class="col-md-8"><label class="form-label">Description</label><textarea v-model="item.description" rows="5" class="form-control"></textarea><div class="selected-subjects mt-2" v-if="item.subjects?.length"><span v-for="code in item.subjects" :key="code" class="badge text-bg-light border me-1 mb-1">{{ subjectNames([code]) }}</span></div></div></div>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <div v-if="isDraft" class="save-bar mt-3">
            <div><strong>Draft changes</strong><div class="tiny text-muted">Save the complete template as one versioned document.</div></div>
            <button class="btn btn-primary" @click="save" :disabled="saving"><span v-if="saving" class="spinner-border spinner-border-sm me-2"></span><i v-else class="bi bi-save me-2"></i>Save draft</button>
          </div>
        </fieldset>
      </div>
    </div>
  </div>
</template>

<style scoped>
.curriculum-sidebar { top: 92px; }
.template-list { max-height: 70vh; overflow-y: auto; }
.template-list .list-group-item.active { background: var(--sl-primary); border-color: var(--sl-primary); color: #fff; }
.count-card { position: relative; border: 1px solid #e8edf3; background: #f9fbfd; border-radius: 11px; padding: 12px; min-height: 75px; color: var(--sl-ink); transition: .15s ease; }
.count-card:hover { border-color: #c6d7f2; background: #f4f8ff; }
.count-card span { display: block; color: #6b7280; font-size: .68rem; margin-bottom: 5px; }
.count-card strong { font-size: 1.2rem; }
.count-card i { position: absolute; right: 11px; bottom: 11px; color: #9aa4b2; }
.section-title { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.curriculum-tabs { display: flex; gap: 5px; overflow-x: auto; padding: 4px; background: #fff; border: 1px solid #e8edf3; border-radius: 12px; box-shadow: 0 3px 14px rgba(23,32,51,.03); }
.tab-button { flex: 0 0 auto; border: 0; background: transparent; color: #64748b; border-radius: 9px; padding: 9px 12px; font-size: .76rem; font-weight: 600; white-space: nowrap; }
.tab-button:hover { background: #f4f7fb; color: var(--sl-primary); }
.tab-button.active { background: #eaf1ff; color: var(--sl-primary); }
.flow-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.flow-card { border: 1px solid #edf1f5; border-radius: 11px; padding: 13px; display: flex; align-items: center; gap: 10px; cursor: pointer; }
.flow-card:hover { border-color: #cddbf2; background: #fafcff; }
.flow-icon { width: 34px; height: 34px; border-radius: 9px; background: #eef4ff; color: var(--sl-primary); display: flex; align-items: center; justify-content: center; flex: 0 0 34px; }
.flow-card strong { font-size: .8rem; }
.flow-card p { margin: 2px 0 0; color: #8a94a3; font-size: .68rem; }
.flow-card > span { margin-left: auto; font-weight: 700; font-size: .8rem; }
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
