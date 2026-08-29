<template>
  <div class="app-page" dir="rtl">
    <AppHeader />

    <main class="page-container projects-page">
      <header class="projects-heading">
        <div>
          <span class="eyebrow"><i class="fas fa-folder-open" aria-hidden="true"></i> مساحة العمل</span>
          <h1 class="page-heading">مشاريعي</h1>
          <p class="page-lead">المخططات التي رفعتها، وحالة كل تحليل، وآخر نسخة يمكنك مراجعتها أو تعديلها.</p>
        </div>
        <RouterLink to="/" class="button button--primary">
          <i class="fas fa-plus" aria-hidden="true"></i> مخطط جديد
        </RouterLink>
      </header>

      <section class="surface projects-tools" aria-label="البحث والتصفية">
        <label class="search-field">
          <span class="sr-only">ابحث باسم المخطط</span>
          <i class="fas fa-magnifying-glass" aria-hidden="true"></i>
          <input v-model.trim="searchQuery" type="search" placeholder="ابحث باسم المخطط…">
        </label>

        <div class="filter-tabs" role="group" aria-label="تصفية حالة المشاريع">
          <button
            v-for="filter in filters"
            :key="filter.value"
            type="button"
            :aria-pressed="activeFilter === filter.value"
            @click="activeFilter = filter.value"
          >
            {{ filter.label }}
          </button>
        </div>
      </section>

      <div v-if="errorMessage" class="notice notice--danger projects-notice" role="alert">
        <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
        <span>{{ errorMessage }}</span>
        <button class="button button--secondary button--small" type="button" @click="fetchProjects">إعادة المحاولة</button>
      </div>

      <section v-if="loading" class="projects-list" aria-label="جاري تحميل المشاريع" aria-busy="true">
        <div v-for="item in 4" :key="item" class="surface project-row project-row--loading">
          <span class="skeleton skeleton--image"></span>
          <span class="skeleton skeleton--text"></span>
          <span class="skeleton skeleton--meta"></span>
        </div>
      </section>

      <section v-else-if="projects.length" class="projects-list" aria-label="قائمة المشاريع">
        <article v-for="project in projects" :key="project.id" class="surface project-row">
          <button class="project-preview" type="button" :aria-label="`فتح ${project.title}`" @click="openProject(project)">
            <img
              v-if="project.analyzed_image_url || project.original_image_url"
              :src="project.analyzed_image_url || project.original_image_url"
              :alt="`معاينة ${project.title}`"
              @error="hideBrokenImage"
            >
            <i class="fas fa-compass-drafting" aria-hidden="true"></i>
          </button>

          <div class="project-main">
            <div class="project-title-line">
              <div>
                <h2>{{ project.title }}</h2>
                <p>{{ formatDate(project.created_at) }}</p>
              </div>
              <span class="badge" :class="statusMeta(project).className">
                <i :class="statusMeta(project).icon" aria-hidden="true"></i>
                {{ statusMeta(project).label }}
              </span>
            </div>

            <dl class="project-meta">
              <div>
                <dt>الغرف</dt>
                <dd>{{ project.rooms_count ?? '—' }}</dd>
              </div>
              <div>
                <dt>الملاحظات</dt>
                <dd>{{ project.violations_count ?? '—' }}</dd>
              </div>
              <div>
                <dt>نتيجة الفحص الأولي</dt>
                <dd>{{ scoreLabel(project.compliance_score) }}</dd>
              </div>
            </dl>
          </div>

          <div class="project-actions">
            <RouterLink :to="`/projects/${project.id}`" class="button button--secondary">
              {{ project.status === 'processing' ? 'متابعة التحليل' : 'فتح المشروع' }}
              <i class="fas fa-arrow-left" aria-hidden="true"></i>
            </RouterLink>
          </div>
        </article>
      </section>

      <section v-else class="surface empty-projects">
        <span class="empty-projects__icon"><i class="fas fa-folder-plus" aria-hidden="true"></i></span>
        <h2>لا توجد مشاريع بعد</h2>
        <p>{{ searchQuery || activeFilter !== 'all' ? 'لا توجد نتائج مطابقة للبحث أو الفلتر الحالي.' : 'ارفع مخطط دور واحد ليظهر التحليل ومراحل التعديل هنا.' }}</p>
        <button v-if="searchQuery || activeFilter !== 'all'" class="button button--secondary" type="button" @click="clearFilters">مسح البحث والفلتر</button>
        <RouterLink v-else to="/" class="button button--primary">رفع أول مخطط</RouterLink>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppHeader from '../components/AppHeader.vue'
import { api } from '../services/api'

const router = useRouter()
const projects = ref([])
const loading = ref(true)
const errorMessage = ref('')
const searchQuery = ref('')
const activeFilter = ref('all')

const filters = [
  { value: 'all', label: 'الكل' },
  { value: 'compliant', label: 'دون ملاحظات ظاهرة' },
  { value: 'non_compliant', label: 'تحتاج مراجعة' },
]

let searchTimer = null

async function fetchProjects() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await api.projects.list({
      search: searchQuery.value,
      status: activeFilter.value === 'all' ? '' : activeFilter.value,
    })
    projects.value = data.projects || []
  } catch (error) {
    projects.value = []
    errorMessage.value = error.message || 'تعذر تحميل المشاريع. حاول مرة أخرى.'
    if (error.status === 401) router.push('/login')
  } finally {
    loading.value = false
  }
}

function statusMeta(project) {
  if (project.status === 'processing') {
    return { label: 'قيد التحليل', className: 'badge--warning', icon: 'fas fa-circle-notch fa-spin' }
  }
  if (project.status === 'failed') {
    return { label: 'تعذر التحليل', className: 'badge--danger', icon: 'fas fa-circle-xmark' }
  }
  if (project.compliance_status === 'compliant') {
    return { label: 'دون ملاحظات ظاهرة', className: 'badge--success', icon: 'fas fa-circle-check' }
  }
  return { label: 'تحتاج مراجعة', className: 'badge--warning', icon: 'fas fa-triangle-exclamation' }
}

function formatDate(value) {
  if (!value) return 'تاريخ غير متاح'
  return new Intl.DateTimeFormat('ar-SA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function scoreLabel(value) {
  return Number.isFinite(value) ? `${Math.round(value)}%` : 'لم تكتمل'
}

function hideBrokenImage(event) {
  event.target.hidden = true
}

function openProject(project) {
  router.push(`/projects/${project.id}`)
}

function clearFilters() {
  searchQuery.value = ''
  activeFilter.value = 'all'
}

watch([searchQuery, activeFilter], () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(fetchProjects, 250)
})

onMounted(fetchProjects)
onBeforeUnmount(() => window.clearTimeout(searchTimer))
</script>

<style scoped>
.projects-page {
  padding-block: clamp(2rem, 5vw, 4.5rem);
}

.projects-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1.5rem;
}

.projects-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 2rem;
  padding: 0.7rem;
}

.search-field {
  position: relative;
  display: flex;
  min-width: min(100%, 20rem);
  align-items: center;
}

.search-field i {
  position: absolute;
  right: 0.85rem;
  color: var(--emad-muted);
  font-size: 0.8rem;
}

.search-field input {
  width: 100%;
  min-height: 2.7rem;
  padding: 0.55rem 2.35rem 0.55rem 0.8rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.65rem;
  background: var(--emad-surface-subtle);
  color: var(--emad-ink);
  font: inherit;
  font-size: 0.82rem;
  outline: none;
}

.search-field input:focus {
  border-color: var(--emad-accent);
  background: var(--emad-surface);
  box-shadow: 0 0 0 3px rgba(23, 107, 91, 0.1);
}

.filter-tabs {
  display: flex;
  gap: 0.25rem;
  overflow-x: auto;
}

.filter-tabs button {
  min-height: 2.45rem;
  padding: 0.5rem 0.75rem;
  border: 0;
  border-radius: 0.6rem;
  background: transparent;
  color: var(--emad-muted);
  font: inherit;
  font-size: 0.75rem;
  font-weight: 650;
  white-space: nowrap;
  cursor: pointer;
}

.filter-tabs button:hover,
.filter-tabs button[aria-pressed='true'] {
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
}

.projects-notice {
  align-items: center;
  margin-top: 1rem;
}

.projects-notice .button {
  margin-right: auto;
}

.projects-list {
  display: grid;
  gap: 0.7rem;
  margin-top: 1rem;
}

.project-row {
  display: grid;
  grid-template-columns: 8.5rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 1rem;
  padding: 0.8rem;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.project-row:hover {
  border-color: rgba(23, 107, 91, 0.25);
  box-shadow: var(--emad-shadow-md);
}

.project-preview {
  position: relative;
  display: grid;
  width: 8.5rem;
  height: 6rem;
  place-items: center;
  overflow: hidden;
  border: 0;
  border-radius: 0.65rem;
  background-color: #eceeea;
  background-image: linear-gradient(rgba(31, 39, 34, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(31, 39, 34, 0.04) 1px, transparent 1px);
  background-size: 12px 12px;
  color: var(--emad-muted);
  cursor: pointer;
}

.project-preview img {
  position: absolute;
  z-index: 1;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.project-main {
  min-width: 0;
}

.project-title-line {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.project-title-line h2,
.project-title-line p {
  margin: 0;
}

.project-title-line h2 {
  overflow: hidden;
  color: var(--emad-ink);
  font-size: 0.95rem;
  font-weight: 720;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-title-line p {
  margin-top: 0.2rem;
  color: var(--emad-muted);
  font-size: 0.7rem;
}

.project-meta {
  display: flex;
  gap: 1.3rem;
  margin: 0.8rem 0 0;
}

.project-meta div {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
}

.project-meta dt,
.project-meta dd {
  margin: 0;
  font-size: 0.7rem;
}

.project-meta dt {
  color: var(--emad-muted);
}

.project-meta dd {
  color: var(--emad-ink-soft);
  font-weight: 700;
}

.project-actions {
  align-self: center;
}

.project-row--loading {
  min-height: 7.6rem;
}

.skeleton {
  display: block;
  border-radius: 0.55rem;
  background: #e8ebe7;
  animation: pulse 1.4s ease-in-out infinite alternate;
}

.skeleton--image {
  width: 8.5rem;
  height: 6rem;
}

.skeleton--text {
  width: 50%;
  height: 1.2rem;
}

.skeleton--meta {
  width: 7rem;
  height: 2.7rem;
}

.empty-projects {
  display: grid;
  min-height: 25rem;
  place-items: center;
  align-content: center;
  gap: 0.7rem;
  margin-top: 1rem;
  padding: 2rem;
  text-align: center;
}

.empty-projects__icon {
  display: grid;
  width: 3.8rem;
  height: 3.8rem;
  place-items: center;
  border-radius: 1rem;
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
  font-size: 1.3rem;
}

.empty-projects h2,
.empty-projects p {
  margin: 0;
}

.empty-projects h2 {
  font-size: 1.05rem;
}

.empty-projects p {
  max-width: 27rem;
  color: var(--emad-muted);
  font-size: 0.82rem;
}

@keyframes pulse {
  from { opacity: 0.55; }
  to { opacity: 1; }
}

@media (max-width: 760px) {
  .projects-heading,
  .projects-tools {
    align-items: stretch;
    flex-direction: column;
  }

  .project-row {
    grid-template-columns: 5.5rem minmax(0, 1fr);
  }

  .project-preview {
    width: 5.5rem;
    height: 5.5rem;
  }

  .project-actions {
    grid-column: 1 / -1;
  }

  .project-actions .button {
    width: 100%;
  }

  .project-title-line {
    flex-direction: column;
    gap: 0.5rem;
  }

  .project-meta {
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
  }

  .skeleton--image {
    width: 5.5rem;
    height: 5.5rem;
  }
}
</style>