<template>
  <div class="app-shell" dir="rtl">
    <AppHeader />

    <main class="project-page page-container">
      <div v-if="loading" class="surface state-panel" role="status">
        <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i>
        <h1>جاري تحميل المشروع…</h1>
        <p>نسترجع المخطط وآخر نتيجة محفوظة.</p>
      </div>

      <div v-else-if="error" class="surface state-panel state-panel--error" role="alert">
        <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
        <h1>تعذر فتح المشروع</h1>
        <p>{{ error }}</p>
        <div class="state-panel__actions">
          <button type="button" class="button button--primary" @click="loadProject">إعادة المحاولة</button>
          <RouterLink to="/projects" class="button button--secondary">العودة إلى المشاريع</RouterLink>
        </div>
      </div>

      <template v-else-if="project">
        <header class="project-heading">
          <div>
            <div class="project-heading__meta">
              <RouterLink to="/projects" class="back-link"><i class="fas fa-arrow-right" aria-hidden="true"></i> مشاريعي</RouterLink>
              <span class="status-chip" :class="statusClass">
                <i :class="statusIcon" aria-hidden="true"></i> {{ statusLabel }}
              </span>
            </div>
            <h1>{{ project.title || `مشروع #${project.id}` }}</h1>
            <p>آخر نتيجة محفوظة للمخطط، مع فصل ما تم رصده عن الأمور التي تحتاج تحققًا أو مراجعة مختص.</p>
          </div>
          <div class="project-heading__actions">
            <button type="button" class="button button--secondary" @click="loadProject">
              <i class="fas fa-rotate" aria-hidden="true"></i> تحديث الحالة
            </button>
            <RouterLink v-if="!isProcessing && !isFailed" :to="`/projects/${project.id}/editor`" class="button button--primary">
              <i class="fas fa-pen-ruler" aria-hidden="true"></i> فتح المحرر
            </RouterLink>
            <button
              v-if="!isProcessing && !isFailed"
              data-testid="download-report"
              type="button"
              class="button button--secondary"
              :disabled="reportDownloading"
              @click="downloadReport"
            >
              <i :class="reportDownloading ? 'fas fa-circle-notch fa-spin' : 'fas fa-file-arrow-down'" aria-hidden="true"></i>
              {{ reportDownloading ? 'جاري إعداد التقرير…' : 'تنزيل التقرير' }}
            </button>
          </div>
        </header>

        <div v-if="reportMessage" class="notice" :class="reportError ? 'notice--danger' : 'notice--success'" role="status">
          <i :class="reportError ? 'fas fa-circle-exclamation' : 'fas fa-circle-check'" aria-hidden="true"></i>
          <span>{{ reportMessage }}</span>
        </div>

        <section v-if="isProcessing" class="surface processing-panel" aria-live="polite">
          <span class="processing-panel__icon"><i class="fas fa-magnifying-glass-chart" aria-hidden="true"></i></span>
          <div>
            <h2>التحليل ما زال قيد المعالجة</h2>
            <p>لم نُصدر نتيجة بعد. استخدم «تحديث الحالة» لقراءة آخر حالة من الخادم.</p>
          </div>
        </section>

        <section v-else-if="isFailed" class="surface failure-panel" role="alert">
          <i class="fas fa-triangle-exclamation" aria-hidden="true"></i>
          <div>
            <h2>لم يكتمل التحليل</h2>
            <p>{{ project.analysis_error_message || 'تعذر إكمال معالجة الملف. لم تُصدر نتيجة أو درجة امتثال لهذا المخطط.' }}</p>
          </div>
        </section>

        <template v-else>
          <section class="summary-strip" aria-label="ملخص النتيجة">
            <article class="surface summary-primary">
              <span class="summary-primary__label">حالة المراجعة الأولية</span>
              <strong>{{ reviewSummary }}</strong>
              <p>{{ reviewSummaryNote }}</p>
            </article>
            <dl class="surface summary-facts">
              <div>
                <dt>العناصر المرصودة</dt>
                <dd>{{ rooms.length }}</dd>
              </div>
              <div>
                <dt>مشاكل محتملة</dt>
                <dd>{{ potentialIssues.length }}</dd>
              </div>
              <div>
                <dt>النتيجة الأولية</dt>
                <dd>{{ scoreLabel }}</dd>
              </div>
            </dl>
          </section>

          <div class="notice notice--warning evidence-note">
            <i class="fas fa-scale-balanced" aria-hidden="true"></i>
            <span>هذه قراءة آلية أولية وليست اعتمادًا هندسيًا. القياسات دون مقياس مؤكد والمراجع دون رقم صفحة موثق تُعامل كعناصر تحتاج مراجعة مختص.</span>
          </div>

          <section class="project-workspace">
            <article class="surface plan-panel" aria-labelledby="plan-title">
              <header class="panel-heading">
                <div>
                  <span class="eyebrow">المخطط</span>
                  <h2 id="plan-title">الدليل البصري</h2>
                </div>
                <a v-if="project.task_id" :href="`/api/download/${project.task_id}`" class="button button--ghost button--small">
                  <i class="fas fa-download" aria-hidden="true"></i> تنزيل الملف
                </a>
              </header>

              <div v-if="planImageUrl" class="plan-canvas">
                <img :src="planImageUrl" :alt="`مخطط ${project.title || project.id}`">
                <button
                  v-for="room in roomsWithBoxes"
                  :key="room.id"
                  type="button"
                  class="room-overlay"
                  :class="{
                    'room-overlay--issue': room.isCompliant === false,
                    'room-overlay--selected': selectedRoomId === room.id,
                  }"
                  :style="boxStyle(room.box)"
                  :aria-label="`عرض ${roomLabel(room.type)}`"
                  @click="selectedRoomId = room.id"
                >
                  <span>{{ roomLabel(room.type) }}</span>
                </button>
              </div>
              <div v-else class="plan-empty">
                <i class="fas fa-file-image" aria-hidden="true"></i>
                <p>لا توجد صورة قابلة للعرض لهذا المشروع.</p>
              </div>
            </article>

            <aside class="surface findings-panel" aria-labelledby="findings-title">
              <header class="panel-heading">
                <div>
                  <span class="eyebrow">المراجعة</span>
                  <h2 id="findings-title">الملاحظات المحتملة</h2>
                </div>
                <span class="count-badge">{{ potentialIssues.length }}</span>
              </header>

              <div v-if="potentialIssues.length" class="findings-list">
                <button
                  v-for="room in potentialIssues"
                  :key="room.id"
                  type="button"
                  class="finding-card"
                  :class="{ 'finding-card--selected': selectedRoomId === room.id }"
                  @click="selectedRoomId = room.id"
                >
                  <span class="finding-card__status"><i class="fas fa-triangle-exclamation" aria-hidden="true"></i> مشكلة محتملة</span>
                  <strong>{{ roomLabel(room.type) }}</strong>
                  <p>{{ room.ragReason || 'أظهرت القراءة الآلية قيمة تحتاج تحققًا قبل إصدار حكم.' }}</p>
                  <dl>
                    <div><dt>المساحة المرصودة</dt><dd>{{ metricLabel(room.metrics?.area, 'م²') }}</dd></div>
                    <div><dt>أقل بُعد</dt><dd>{{ metricLabel(room.metrics?.minDim, 'م') }}</dd></div>
                  </dl>
                  <small><i class="fas fa-book-open" aria-hidden="true"></i> {{ referenceLabel(room.reference) }}</small>
                </button>
              </div>

              <div v-else class="findings-empty">
                <i class="fas fa-circle-check" aria-hidden="true"></i>
                <h3>لم تظهر مشكلة محتملة في العناصر المقروءة</h3>
                <p>هذا لا يثبت المطابقة الكاملة؛ قد توجد عناصر لم تُقرأ أو قواعد تحتاج قياسًا ومراجعة مختص.</p>
              </div>

              <RouterLink :to="`/projects/${project.id}/editor`" class="button button--primary findings-action">
                {{ potentialIssues.length ? 'مراجعة الحلول في المحرر' : 'فتح المخطط في المحرر' }}
                <i class="fas fa-arrow-left" aria-hidden="true"></i>
              </RouterLink>
            </aside>
          </section>
        </template>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '../components/AppHeader.vue'
import { api } from '../services/api'
import { downloadProjectReport } from '../utils/projectReport'
import { roomLabelAr } from '../utils/roomLabels'

const route = useRoute()
const project = ref(null)
const loading = ref(true)
const error = ref('')
const selectedRoomId = ref(null)
const reportDownloading = ref(false)
const reportMessage = ref('')
const reportError = ref(false)
let pollTimer = null

const rooms = computed(() => Array.isArray(project.value?.rooms_data) ? project.value.rooms_data : [])
const potentialIssues = computed(() => rooms.value.filter((room) => room.isCompliant === false))
const roomsWithBoxes = computed(() => rooms.value.filter((room) => {
  const box = room.box
  return box && ['x', 'y', 'w', 'h'].every((key) => Number.isFinite(Number(box[key])))
}))
const normalizedStatus = computed(() => String(project.value?.status || '').toLowerCase())
const isProcessing = computed(() => ['processing', 'processing_started', 'pending'].includes(normalizedStatus.value))
const isFailed = computed(() => ['failed', 'error'].includes(normalizedStatus.value))
const planImageUrl = computed(() => project.value?.analyzed_image_url || project.value?.original_image_url || '')
const statusLabel = computed(() => {
  if (isProcessing.value) return 'قيد التحليل'
  if (isFailed.value) return 'تعذر التحليل'
  if (normalizedStatus.value === 'completed') return 'اكتمل التحليل'
  return 'حالة غير محددة'
})
const statusClass = computed(() => {
  if (isProcessing.value) return 'status-chip--processing'
  if (isFailed.value) return 'status-chip--failed'
  return 'status-chip--completed'
})
const statusIcon = computed(() => {
  if (isProcessing.value) return 'fas fa-circle-notch fa-spin'
  if (isFailed.value) return 'fas fa-circle-exclamation'
  return 'fas fa-circle-check'
})
const scoreLabel = computed(() => (
  Number.isFinite(Number(project.value?.compliance_score))
    ? `${Math.round(Number(project.value.compliance_score))}%`
    : 'غير متاحة'
))
const reviewSummary = computed(() => (
  potentialIssues.value.length ? 'توجد عناصر تحتاج مراجعة' : 'لا توجد ملاحظة ضمن العناصر المقروءة'
))
const reviewSummaryNote = computed(() => (
  potentialIssues.value.length
    ? `رُصدت ${potentialIssues.value.length} مشكلة محتملة. افتح كل ملاحظة وراجع دليلها قبل اتخاذ قرار.`
    : 'النتيجة محدودة بالعناصر التي استطاع النظام قراءتها والتحقق منها.'
))

function clearPoll() {
  if (pollTimer !== null) {
    window.clearTimeout(pollTimer)
    pollTimer = null
  }
}

function schedulePoll() {
  clearPoll()
  if (!error.value && isProcessing.value) {
    pollTimer = window.setTimeout(() => loadProject({ silent: true }), 3000)
  }
}

async function loadProject(options = {}) {
  clearPoll()
  if (!options.silent) loading.value = true
  error.value = ''
  try {
    project.value = await api.projects.get(route.params.id)
  } catch (requestError) {
    error.value = requestError.message || 'تعذر الاتصال بالخادم.'
  } finally {
    loading.value = false
    schedulePoll()
  }
}

async function downloadReport() {
  if (!project.value || reportDownloading.value) return
  reportDownloading.value = true
  reportMessage.value = ''
  reportError.value = false
  try {
    const report = await api.projects.report(project.value.id)
    downloadProjectReport(report)
    reportMessage.value = `تم تنزيل تقرير النسخة المعتمدة ${report.revision.number}.`
  } catch (requestError) {
    const detail = requestError?.payload?.detail
    reportError.value = true
    reportMessage.value = typeof detail === 'object' && detail?.message
      ? detail.message
      : requestError.message || 'تعذر إعداد التقرير.'
  } finally {
    reportDownloading.value = false
  }
}

function roomLabel(type) {
  return roomLabelAr(type)
}

function metricLabel(value, unit) {
  return Number.isFinite(Number(value)) ? `${Number(value)} ${unit}` : 'غير قابل للتحقق'
}

function referenceLabel(reference) {
  return reference || 'المصدر غير موثق — يحتاج مراجعة مختص'
}

function boxStyle(box) {
  return {
    left: `${Number(box.x) * 100}%`,
    top: `${Number(box.y) * 100}%`,
    width: `${Number(box.w) * 100}%`,
    height: `${Number(box.h) * 100}%`,
  }
}

onMounted(loadProject)
onBeforeUnmount(clearPoll)
</script>

<style scoped>
.project-page { padding-block: clamp(1.3rem, 3vw, 2.5rem); }
.project-heading { display: flex; align-items: end; justify-content: space-between; gap: 1.25rem; margin-bottom: 1.25rem; }
.project-heading h1, .project-heading p, .state-panel h1, .state-panel p, .processing-panel h2, .processing-panel p, .failure-panel h2, .failure-panel p, .summary-primary p, .panel-heading h2, .findings-empty h3, .findings-empty p { margin: 0; }
.project-heading h1 { margin-top: .55rem; color: var(--emad-ink); font-size: clamp(1.55rem, 4vw, 2.2rem); letter-spacing: -.035em; }
.project-heading p { max-width: 44rem; margin-top: .35rem; color: var(--emad-muted); font-size: .78rem; }
.project-heading__meta, .project-heading__actions { display: flex; align-items: center; gap: .65rem; flex-wrap: wrap; }
.back-link { display: inline-flex; align-items: center; gap: .35rem; color: var(--emad-muted); font-size: .72rem; font-weight: 650; text-decoration: none; }
.back-link:hover { color: var(--emad-accent-dark); }
.status-chip { display: inline-flex; align-items: center; gap: .35rem; min-height: 1.8rem; padding-inline: .65rem; border: 1px solid; border-radius: 99px; font-size: .68rem; font-weight: 700; }
.status-chip--completed { border-color: #badbcf; background: #eef8f4; color: var(--emad-accent-dark); }
.status-chip--processing { border-color: #bfd4e9; background: #eef6fd; color: #235f96; }
.status-chip--failed { border-color: #ecc3bf; background: #fff2f1; color: var(--emad-danger); }
.state-panel { display: grid; min-height: 24rem; place-items: center; align-content: center; gap: .7rem; padding: 2rem; text-align: center; }
.state-panel > i { color: var(--emad-accent); font-size: 1.8rem; }
.state-panel h1 { font-size: 1.2rem; }
.state-panel p { color: var(--emad-muted); font-size: .78rem; }
.state-panel--error > i { color: var(--emad-danger); }
.state-panel__actions { display: flex; gap: .6rem; margin-top: .7rem; }
.processing-panel, .failure-panel { display: flex; align-items: center; gap: 1rem; padding: 1.2rem; }
.processing-panel__icon { display: grid; width: 3rem; height: 3rem; place-items: center; border-radius: .75rem; background: #eef6fd; color: #235f96; }
.processing-panel h2, .failure-panel h2 { font-size: .95rem; }
.processing-panel p, .failure-panel p { margin-top: .25rem; color: var(--emad-muted); font-size: .74rem; }
.failure-panel { border-color: #ecc3bf; background: #fff9f8; }
.failure-panel > i { color: var(--emad-danger); font-size: 1.2rem; }
.summary-strip { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(25rem, .85fr); gap: 1rem; }
.summary-primary, .summary-facts { padding: 1.15rem 1.25rem; }
.summary-primary__label { color: var(--emad-muted); font-size: .68rem; }
.summary-primary strong { display: block; margin-top: .35rem; color: var(--emad-ink); font-size: 1.05rem; }
.summary-primary p { margin-top: .25rem; color: var(--emad-muted); font-size: .72rem; }
.summary-facts { display: grid; grid-template-columns: repeat(3, 1fr); margin: 0; }
.summary-facts div { padding-inline: 1rem; border-left: 1px solid var(--emad-line); }
.summary-facts div:last-child { border-left: 0; }
.summary-facts dt { color: var(--emad-muted); font-size: .66rem; }
.summary-facts dd { margin: .3rem 0 0; color: var(--emad-ink); font-size: 1rem; font-weight: 760; }
.evidence-note { margin-top: 1rem; }
.project-workspace { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(19rem, .55fr); gap: 1rem; align-items: start; margin-top: 1rem; }
.plan-panel, .findings-panel { overflow: hidden; }
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 1.1rem; border-bottom: 1px solid var(--emad-line); }
.panel-heading h2 { margin-top: .25rem; font-size: .92rem; }
.count-badge { display: grid; min-width: 2rem; height: 2rem; place-items: center; border-radius: 99px; background: var(--emad-warning-soft); color: #7a571b; font-size: .72rem; font-weight: 760; }
.plan-canvas { position: relative; display: grid; min-height: 30rem; place-items: center; overflow: auto; padding: 1.25rem; background-color: #eef1ed; background-image: linear-gradient(rgba(31,39,34,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(31,39,34,.035) 1px, transparent 1px); background-size: 22px 22px; }
.plan-canvas img { display: block; max-width: 100%; max-height: 68vh; object-fit: contain; box-shadow: 0 8px 24px rgba(27, 38, 31, .12); }
.room-overlay { position: absolute; border: 2px solid var(--emad-accent); background: rgba(23,107,91,.08); color: transparent; cursor: pointer; }
.room-overlay span { position: absolute; top: -1.7rem; right: 0; padding: .2rem .4rem; border-radius: .3rem; background: var(--emad-ink); color: white; font-size: .6rem; opacity: 0; white-space: nowrap; }
.room-overlay:hover span, .room-overlay:focus-visible span, .room-overlay--selected span { opacity: 1; }
.room-overlay--issue { border-color: #c48216; background: rgba(196,130,22,.11); }
.room-overlay--selected { outline: 3px solid rgba(44,116,181,.35); outline-offset: 2px; }
.plan-empty { display: grid; min-height: 28rem; place-items: center; align-content: center; gap: .6rem; color: var(--emad-muted); }
.plan-empty i { font-size: 1.6rem; }
.plan-empty p { font-size: .75rem; }
.findings-list { display: grid; gap: .7rem; max-height: 57vh; overflow-y: auto; padding: .9rem; }
.finding-card { display: grid; gap: .45rem; width: 100%; min-height: 44px; padding: .85rem; border: 1px solid var(--emad-line); border-radius: .75rem; background: var(--emad-surface); color: inherit; text-align: right; cursor: pointer; }
.finding-card:hover, .finding-card--selected { border-color: #c48216; background: #fffaf0; }
.finding-card__status { display: inline-flex; align-items: center; gap: .35rem; color: #825b17; font-size: .64rem; font-weight: 750; }
.finding-card strong { font-size: .84rem; }
.finding-card p { margin: 0; color: var(--emad-muted); font-size: .7rem; line-height: 1.65; }
.finding-card dl { display: grid; grid-template-columns: 1fr 1fr; margin: .15rem 0 0; }
.finding-card dl div { padding: .55rem; background: var(--emad-surface-subtle); }
.finding-card dt { color: var(--emad-muted); font-size: .6rem; }
.finding-card dd { margin: .2rem 0 0; font-size: .7rem; font-weight: 700; }
.finding-card small { display: flex; gap: .35rem; align-items: start; padding-top: .45rem; border-top: 1px solid var(--emad-line); color: var(--emad-muted); font-size: .6rem; line-height: 1.5; }
.findings-empty { display: grid; min-height: 18rem; place-items: center; align-content: center; gap: .45rem; padding: 1.25rem; text-align: center; }
.findings-empty > i { color: var(--emad-accent); font-size: 1.5rem; }
.findings-empty h3 { font-size: .84rem; }
.findings-empty p { max-width: 18rem; color: var(--emad-muted); font-size: .68rem; line-height: 1.65; }
.findings-action { margin: .9rem; }
@media (max-width: 950px) { .summary-strip, .project-workspace { grid-template-columns: 1fr; } }
@media (max-width: 680px) { .project-heading { align-items: stretch; flex-direction: column; } .project-heading__actions > * { flex: 1; } .summary-facts { grid-template-columns: 1fr; } .summary-facts div { padding: .7rem 0; border-bottom: 1px solid var(--emad-line); border-left: 0; } .summary-facts div:last-child { border-bottom: 0; } .plan-canvas { min-height: 22rem; } }
</style>