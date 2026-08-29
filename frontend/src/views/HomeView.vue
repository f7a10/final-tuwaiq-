<template>
  <div class="app-page" dir="rtl">
    <AppHeader />

    <main class="home-main">
      <section class="page-container upload-intro" aria-labelledby="upload-title">
        <div>
          <span class="eyebrow"><i class="fas fa-house" aria-hidden="true"></i> البداية</span>
          <h1 id="upload-title" class="page-heading">ابدأ بصورة مخطط منزلك</h1>
          <p class="page-lead">
            ارفع مخطط دور واحد. سنرتّب لك الغرف والملاحظات، ثم نعرض التعديلات المقترحة للمراجعة قبل اعتماد أي تغيير.
          </p>
        </div>

        <ol class="journey" aria-label="خطوات العمل">
          <li><strong>1</strong><span>ارفع المخطط</span></li>
          <li><strong>2</strong><span>راجع التحليل</span></li>
          <li><strong>3</strong><span>جرّب التعديلات</span></li>
        </ol>
      </section>

      <section class="page-container upload-layout" aria-label="رفع المخطط وإعداد التحليل">
        <form class="surface upload-card" @submit.prevent="uploadAndAnalyze">
          <label
            class="drop-zone"
            :class="{ 'drop-zone--active': isDragging, 'drop-zone--selected': selectedFile }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              class="sr-only"
              type="file"
              accept="application/pdf,image/png,image/jpeg"
              @change="handleFileSelect"
            >

            <template v-if="!selectedFile">
              <span class="drop-zone__icon"><i class="fas fa-arrow-up-from-bracket" aria-hidden="true"></i></span>
              <strong>اختر الملف أو اسحبه إلى هنا</strong>
              <span>PDF أو PNG أو JPG — حتى 10MB</span>
              <span class="button button--secondary button--small" aria-hidden="true">اختيار ملف</span>
            </template>

            <template v-else>
              <img v-if="previewUrl" :src="previewUrl" alt="معاينة المخطط المختار" class="file-preview">
              <span v-else class="drop-zone__icon drop-zone__icon--pdf"><i class="fas fa-file-pdf" aria-hidden="true"></i></span>
              <strong class="file-name">{{ selectedFile.name }}</strong>
              <span>{{ formatFileSize(selectedFile.size) }}</span>
              <span class="button button--secondary button--small" aria-hidden="true">اختيار ملف آخر</span>
            </template>
          </label>

          <div v-if="fileError" class="notice notice--danger" role="alert">
            <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
            <span>{{ fileError }}</span>
          </div>

          <div class="field">
            <label for="project-title" class="field__label">اسم المخطط</label>
            <input
              id="project-title"
              v-model.trim="projectTitle"
              class="input"
              type="text"
              maxlength="120"
              placeholder="مثال: الدور الأرضي — منزل العائلة"
            >
            <p class="field__hint">سيظهر بهذا الاسم في قائمة مشاريعك.</p>
          </div>

          <div v-if="uploadError" class="notice notice--danger" role="alert">
            <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
            <span>{{ uploadError }}</span>
          </div>

          <button class="button button--primary upload-submit" type="submit" :disabled="!canSubmit || isUploading">
            <i v-if="isUploading" class="fas fa-circle-notch fa-spin" aria-hidden="true"></i>
            <i v-else class="fas fa-magnifying-glass" aria-hidden="true"></i>
            <span>{{ submitLabel }}</span>
          </button>

          <p v-if="!authStore.isAuthenticated" class="login-hint">
            لديك حساب؟ <RouterLink to="/login">سجّل الدخول</RouterLink> قبل بدء التحليل.
          </p>
        </form>

        <aside class="upload-guide" aria-label="ما الذي سيقدمه التحليل">
          <div class="surface guide-section">
            <span class="guide-section__label">ما الذي ستحصل عليه؟</span>
            <ul class="guide-list">
              <li>
                <i class="fas fa-vector-square" aria-hidden="true"></i>
                <span><strong>قراءة مبسطة للمخطط</strong><small>الغرف والعناصر والأبعاد المتاحة.</small></span>
              </li>
              <li>
                <i class="fas fa-list-check" aria-hidden="true"></i>
                <span><strong>ملاحظات قابلة للمراجعة</strong><small>مع الإشارة إلى سبب كل ملاحظة والدليل المتوفر.</small></span>
              </li>
              <li>
                <i class="fas fa-pen-ruler" aria-hidden="true"></i>
                <span><strong>بدائل تعديل قبل الاعتماد</strong><small>يمكنك المقارنة والتراجع قبل حفظ النسخة الجديدة.</small></span>
              </li>
            </ul>
          </div>

          <div class="notice notice--warning preliminary-notice">
            <i class="fas fa-shield-halved" aria-hidden="true"></i>
            <p>
              <strong>النتائج إرشادية أولية.</strong>
              التحقق النهائي من كود البناء والقرارات الإنشائية يبقى لدى المختص المرخّص.
            </p>
          </div>

          <p class="privacy-note"><i class="fas fa-lock" aria-hidden="true"></i> لا نغيّر الملف الأصلي؛ كل تعديل يبدأ كمعاينة منفصلة.</p>
        </aside>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppHeader from '../components/AppHeader.vue'
import { api } from '../services/api'
import { useAnalysisStore } from '../stores/analysis'
import { useAuthStore } from '../stores/auth'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const SUPPORTED_TYPES = new Set(['application/pdf', 'image/png', 'image/jpeg'])

const router = useRouter()
const analysisStore = useAnalysisStore()
const authStore = useAuthStore()

const fileInput = ref(null)
const selectedFile = ref(null)
const previewUrl = ref('')
const projectTitle = ref('')
const fileError = ref('')
const uploadError = ref('')
const isDragging = ref(false)
const isUploading = ref(false)

const canSubmit = computed(() => Boolean(selectedFile.value && projectTitle.value))
const submitLabel = computed(() => {
  if (isUploading.value) return 'جاري رفع المخطط…'
  if (!authStore.isAuthenticated) return 'سجّل الدخول لبدء التحليل'
  return 'بدء تحليل المخطط'
})

function releasePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

function selectFile(file) {
  fileError.value = ''
  uploadError.value = ''

  if (!SUPPORTED_TYPES.has(file.type)) {
    fileError.value = 'صيغة الملف غير مدعومة. اختر PDF أو PNG أو JPG.'
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    fileError.value = 'حجم الملف أكبر من 10MB. صغّر الملف ثم حاول مرة أخرى.'
    return
  }

  releasePreview()
  selectedFile.value = file
  if (file.type.startsWith('image/')) previewUrl.value = URL.createObjectURL(file)
  if (!projectTitle.value) projectTitle.value = file.name.replace(/\.[^.]+$/, '')
}

function handleFileSelect(event) {
  const [file] = event.target.files || []
  if (file) selectFile(file)
}

function handleDrop(event) {
  isDragging.value = false
  const [file] = event.dataTransfer.files || []
  if (file) selectFile(file)
}

function formatFileSize(bytes) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function uploadAndAnalyze() {
  if (!canSubmit.value || isUploading.value) return
  if (!authStore.isAuthenticated) {
    router.push({ name: 'login', query: { redirect: '/' } })
    return
  }

  isUploading.value = true
  uploadError.value = ''
  try {
    const data = await api.projects.upload(selectedFile.value, {
      title: projectTitle.value,
      checkVentilation: true,
      checkDimensions: true,
      floorCount: 1,
    })
    analysisStore.setAnalysis({
      id: data.project_id,
      taskId: data.task_id,
      imageUrl: data.image_url,
      rooms: [],
      status: data.status || 'processing',
      title: projectTitle.value,
      date: new Date().toISOString(),
    })
    await router.push(`/projects/${data.project_id}`)
  } catch (error) {
    uploadError.value = error.message || 'تعذر رفع المخطط. تحقق من الاتصال وحاول مرة أخرى.'
  } finally {
    isUploading.value = false
  }
}

onBeforeUnmount(releasePreview)
</script>

<style scoped>
.home-main {
  padding-bottom: 4rem;
}

.upload-intro {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 2rem;
  padding-block: clamp(2.5rem, 6vw, 5.5rem) 2rem;
}

.journey {
  display: flex;
  gap: 0;
  margin: 0;
  padding: 0;
  color: var(--emad-muted);
  font-size: 0.75rem;
  list-style: none;
}

.journey li {
  position: relative;
  display: grid;
  min-width: 6.6rem;
  justify-items: center;
  gap: 0.35rem;
}

.journey li:not(:last-child)::after {
  position: absolute;
  top: 0.85rem;
  right: calc(50% + 1rem);
  width: calc(100% - 2rem);
  height: 1px;
  background: var(--emad-line-strong);
  content: '';
  transform: translateX(-100%);
}

.journey strong {
  display: grid;
  z-index: 1;
  width: 1.75rem;
  height: 1.75rem;
  place-items: center;
  border: 1px solid var(--emad-line-strong);
  border-radius: 50%;
  background: var(--emad-surface);
  color: var(--emad-accent-dark);
  font-size: 0.7rem;
}

.upload-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(17rem, 0.75fr);
  gap: 1rem;
  align-items: start;
}

.upload-card {
  display: grid;
  gap: 1rem;
  padding: clamp(1rem, 2vw, 1.5rem);
}

.drop-zone {
  display: flex;
  min-height: 23rem;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 0.65rem;
  padding: 2rem;
  border: 1.5px dashed var(--emad-line-strong);
  border-radius: 0.9rem;
  background: var(--emad-surface-subtle);
  color: var(--emad-muted);
  text-align: center;
  cursor: pointer;
  transition: border-color 150ms ease, background-color 150ms ease, box-shadow 150ms ease;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: var(--emad-accent);
  background: var(--emad-accent-soft);
  box-shadow: inset 0 0 0 1px rgba(23, 107, 91, 0.08);
}

.drop-zone--selected {
  min-height: 25rem;
  background: #f6f7f4;
}

.drop-zone strong {
  color: var(--emad-ink);
  font-size: 1.02rem;
}

.drop-zone__icon {
  display: grid;
  width: 3.4rem;
  height: 3.4rem;
  margin-bottom: 0.25rem;
  place-items: center;
  border-radius: 0.9rem;
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
  font-size: 1.25rem;
}

.drop-zone__icon--pdf {
  background: var(--emad-danger-soft);
  color: var(--emad-danger);
}

.file-preview {
  width: min(100%, 42rem);
  max-height: 17rem;
  margin-bottom: 0.5rem;
  object-fit: contain;
}

.file-name {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-submit {
  width: 100%;
  min-height: 3.35rem;
}

.login-hint {
  margin: -0.25rem 0 0;
  color: var(--emad-muted);
  font-size: 0.78rem;
  text-align: center;
}

.login-hint a {
  color: var(--emad-accent-dark);
  font-weight: 700;
}

.upload-guide {
  display: grid;
  gap: 0.8rem;
}

.guide-section {
  padding: 1.25rem;
}

.guide-section__label {
  color: var(--emad-ink);
  font-size: 0.88rem;
  font-weight: 720;
}

.guide-list {
  display: grid;
  gap: 0;
  margin: 0.75rem 0 0;
  padding: 0;
  list-style: none;
}

.guide-list li {
  display: grid;
  grid-template-columns: 2.25rem 1fr;
  gap: 0.75rem;
  padding-block: 0.85rem;
  border-top: 1px solid var(--emad-line);
}

.guide-list i {
  display: grid;
  width: 2.25rem;
  height: 2.25rem;
  place-items: center;
  border-radius: 0.65rem;
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
}

.guide-list strong,
.guide-list small {
  display: block;
}

.guide-list strong {
  color: var(--emad-ink-soft);
  font-size: 0.82rem;
}

.guide-list small {
  margin-top: 0.15rem;
  color: var(--emad-muted);
  font-size: 0.72rem;
  line-height: 1.65;
}

.preliminary-notice p {
  margin: 0;
}

.preliminary-notice strong {
  display: block;
  margin-bottom: 0.15rem;
}

.privacy-note {
  margin: 0;
  padding-inline: 0.25rem;
  color: var(--emad-muted);
  font-size: 0.72rem;
}

.privacy-note i {
  margin-left: 0.35rem;
  color: var(--emad-accent);
}

@media (max-width: 900px) {
  .upload-intro,
  .upload-layout {
    grid-template-columns: 1fr;
  }

  .journey {
    justify-content: center;
  }
}

@media (max-width: 560px) {
  .upload-intro {
    gap: 1.5rem;
  }

  .journey {
    width: 100%;
  }

  .journey li {
    min-width: 0;
    flex: 1;
  }

  .drop-zone {
    min-height: 18rem;
    padding: 1rem;
  }
}
</style>