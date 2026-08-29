<template>
  <div class="editor-page" dir="rtl">
    <header class="editor-header">
      <div class="editor-header__identity">
        <RouterLink class="icon-button" :to="`/projects/${projectId}`" aria-label="العودة إلى نتيجة المشروع">
          <i class="fas fa-arrow-right" aria-hidden="true"></i>
        </RouterLink>
        <BrandMark />
        <div>
          <h1>تعديل المخطط</h1>
          <p>المشروع {{ shortProjectId }} · النسخة المعتمدة {{ revision }}</p>
        </div>
      </div>

      <div class="editor-header__actions">
        <button data-testid="undo-change" class="button button--secondary button--small" type="button" :disabled="!sessionState?.can_undo || busy" @click="undo">
          <i class="fas fa-rotate-right" aria-hidden="true"></i> تراجع
        </button>
        <button data-testid="redo-change" class="button button--secondary button--small" type="button" :disabled="!sessionState?.can_redo || busy" @click="redo">
          <i class="fas fa-rotate-left" aria-hidden="true"></i> إعادة
        </button>
        <span class="badge" :class="scaleConfirmed ? 'badge--success' : 'badge--warning'">
          <i :class="scaleConfirmed ? 'fas fa-circle-check' : 'fas fa-triangle-exclamation'" aria-hidden="true"></i>
          المقياس {{ scalePercent }}%
        </span>
      </div>
    </header>

    <main class="editor-shell">
      <aside class="editor-panel selection-panel" aria-labelledby="selection-title">
        <div class="panel-heading">
          <span class="panel-step">1</span>
          <div>
            <h2 id="selection-title">اختر من المخطط</h2>
            <p>ابدأ بالغرفة ثم اختر العنصر.</p>
          </div>
        </div>

        <div class="selection-path" aria-live="polite">
          <span v-if="!selectedRoom">لم تختر عنصرًا بعد</span>
          <template v-else>
            <b>{{ selectedRoomLabel }}</b>
            <i class="fas fa-chevron-left" aria-hidden="true"></i>
            <b v-if="selectedWall">{{ selectedWallLabel }}</b>
          </template>
        </div>

        <section class="element-group">
          <h3>الغرف</h3>
          <button
            v-for="room in approvedRooms"
            :key="room.id"
            :data-testid="`room-${room.id}`"
            type="button"
            class="element-button"
            :class="{ 'element-button--selected': selectedRoom === room.id }"
            @click="selectRoom(room.id)"
          >
            <span><i class="fas fa-vector-square" aria-hidden="true"></i> {{ roomLabelAr(room.label) }}</span>
            <small>{{ Number(room.area_m2).toFixed(1) }} م²</small>
          </button>
        </section>

        <section class="element-group">
          <h3>الجدران المشتركة القابلة للمعاينة</h3>
          <button
            v-for="wall in approvedWalls"
            :key="wall.id"
            data-testid="wall-option"
            type="button"
            class="element-button"
            :class="{ 'element-button--selected': selectedElement === wall.id }"
            @click="selectElement(wall.id)"
          >
            <span><i class="fas fa-grip-lines-vertical" aria-hidden="true"></i> {{ wallLabel(wall) }}</span>
            <small>{{ wall.structural_status === 'unknown' ? 'حالته الإنشائية غير مؤكدة' : 'مراجع' }}</small>
          </button>
        </section>

        <p class="panel-tip"><i class="fas fa-circle-info" aria-hidden="true"></i> الأبواب والنوافذ تظهر في نتائج التحليل، لكن تعديلها الحتمي ليس ضمن نسخة العرض الحالية.</p>
      </aside>

      <section class="canvas-column" aria-labelledby="canvas-title">
        <div class="canvas-toolbar">
          <div>
            <span class="badge" :class="hasPreview ? 'badge--preview' : 'badge--success'">
              {{ hasPreview ? 'معاينة مؤقتة' : 'الحالة المعتمدة' }}
            </span>
            <h2 id="canvas-title">المخطط التفاعلي</h2>
          </div>
          <button class="button button--secondary button--small" type="button" :disabled="!hasPreview" @click="showComparison = !showComparison">
            {{ showComparison ? 'إخفاء المقترح' : 'إظهار قبل / بعد' }}
          </button>
        </div>

        <div class="canvas-wrap" :class="{ 'canvas-wrap--preview': hasPreview }">
          <div v-if="loading" class="canvas-state" role="status">
            <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> جاري تحميل المخطط المحفوظ…
          </div>
          <svg v-else-if="approvedGeometry" :viewBox="planViewBox" role="img" aria-label="المخطط الهندسي المستخرج من نتيجة التحليل">
            <g v-for="room in approvedRooms" :key="room.id">
              <rect
                :x="room.x_mm"
                :y="room.y_mm"
                :width="room.width_mm"
                :height="room.height_mm"
                class="room-fill room-outline"
                :class="{ 'room-fill--selected': selectedRoom === room.id }"
                tabindex="0"
                @click="selectRoom(room.id)"
              />
              <text :x="room.x_mm + room.width_mm / 2" :y="room.y_mm + room.height_mm / 2" class="room-label" :style="labelStyle">{{ roomLabelAr(room.label) }}</text>
              <text :x="room.x_mm + room.width_mm / 2" :y="room.y_mm + room.height_mm / 2 + labelGap" class="room-area" :style="areaStyle">{{ Number(room.area_m2).toFixed(1) }} م²</text>
            </g>

            <line
              v-for="wall in approvedWalls"
              :key="wall.id"
              v-bind="wallLine(wall)"
              class="current-wall"
              :class="{ 'current-wall--selected': selectedElement === wall.id }"
              tabindex="0"
              @click="selectElement(wall.id)"
            />

            <g v-if="hasPreview && showComparison" class="proposal-layer">
              <line
                v-for="wall in previewWalls"
                :key="wall.id"
                v-bind="wallLine(wall)"
                class="proposal-wall"
              />
            </g>
          </svg>
          <div v-else class="canvas-state" role="alert">تعذر إنشاء geometry قابلة للتعديل لهذا المخطط.</div>

          <div class="canvas-legend">
            <span><i class="legend-current"></i> المعتمد</span>
            <span><i class="legend-proposal"></i> المقترح</span>
          </div>
        </div>

        <div class="editor-message" :class="`editor-message--${messageTone}`" role="status" aria-live="polite">
          <i :class="messageTone === 'warning' ? 'fas fa-triangle-exclamation' : 'fas fa-circle-info'" aria-hidden="true"></i>
          {{ message }}
        </div>
      </section>

      <aside class="editor-panel action-panel" aria-labelledby="action-title">
        <div class="panel-heading">
          <span class="panel-step">2</span>
          <div>
            <h2 id="action-title">أنشئ التعديل</h2>
            <p>كل تغيير يبدأ كمعاينة.</p>
          </div>
        </div>

        <section v-if="!scaleConfirmed || !geometryConfirmed" class="draft-confirmation" aria-labelledby="draft-confirmation-title">
          <div>
            <span class="badge badge--warning">خطوة مطلوبة</span>
            <h3 id="draft-confirmation-title">راجع الرسم والمقياس</h3>
            <p>قارن حدود الغرف والقياسات الظاهرة بالمخطط الأصلي قبل السماح بأي اعتماد متري.</p>
          </div>
          <label>
            <input v-model="draftGeometryConfirmed" data-testid="confirm-geometry" type="checkbox">
            <span>راجعت حدود الغرف والجدران الظاهرة وهي مطابقة للمخطط المرفوع.</span>
          </label>
          <label>
            <input v-model="draftScaleConfirmed" data-testid="confirm-scale" type="checkbox">
            <span>راجعت القياسات المعروضة وأؤكد استخدامها في معاينات هذه الجلسة.</span>
          </label>
          <button
            data-testid="confirm-draft"
            class="button button--primary"
            type="button"
            :disabled="!draftGeometryConfirmed || !draftScaleConfirmed || busy"
            @click="confirmDraft"
          >
            تأكيد الرسم والمقياس
          </button>
        </section>

        <section v-if="selectedWall" class="action-section">
          <label for="wall-offset">تحريك الجدار المشترك</label>
          <div class="number-field">
            <input id="wall-offset" data-testid="wall-offset" v-model="wallOffset" type="number" min="-150" max="150" step="10">
            <span>سم</span>
          </div>
          <p>القيمة الموجبة تزيد مساحة {{ positiveRoomLabel }}. المجال من −150 إلى 150 سم.</p>
          <button data-testid="create-preview" class="button button--primary" type="button" :disabled="busy" @click="createPreview">إنشاء معاينة</button>
        </section>

        <section v-else class="empty-action">
          <i class="fas fa-arrow-pointer" aria-hidden="true"></i>
          <strong>{{ selectedRoom ? 'اختر جدارًا مشتركًا' : 'اختر غرفة للبدء' }}</strong>
          <p>ستظهر أدوات العنصر هنا بعد اختياره.</p>
        </section>

        <section class="action-section prompt-section">
          <label for="edit-prompt">أو اكتب التعديل المطلوب</label>
          <textarea id="edit-prompt" v-model="prompt" rows="3" placeholder="مثال: حرّك الجدار 50 سم نحو غرفة النوم"></textarea>
          <button
            data-testid="ai-preview"
            class="button button--secondary"
            type="button"
            :disabled="aiPlanning"
            @click="createPromptPreview"
          >
            <i :class="aiPlanning ? 'fas fa-circle-notch fa-spin' : 'fas fa-wand-magic-sparkles'" aria-hidden="true"></i>
            {{ aiPlanning ? 'جاري فهم الطلب…' : 'فهم الطلب وإنشاء معاينة' }}
          </button>
        </section>

        <section v-if="hasPreview" class="preview-panel" data-testid="preview-status">
          <div class="preview-panel__heading">
            <span class="badge badge--preview">لم تعتمد</span>
            <strong>راجع أثر التعديل</strong>
          </div>
          <ul>
            <li>{{ selectedWallLabel }}: تحريك {{ previewDelta }} سم</li>
            <li v-for="comparison in affectedRoomComparisons" :key="comparison.id">
              {{ comparison.label }}: {{ comparison.before.toFixed(1) }} ← {{ comparison.after.toFixed(1) }} م²
            </li>
          </ul>
          <label v-if="selectedWall?.structural_status === 'unknown'" class="structural-confirmation">
            <input v-model="structuralReviewConfirmed" data-testid="structural-review" type="checkbox">
            <span>أفهم أن الحالة الإنشائية لهذا الجدار غير مؤكدة، وسأراجعها مع مختص قبل التنفيذ الفعلي.</span>
          </label>
          <div class="preview-actions">
            <button data-testid="approve-change" class="button button--primary" type="button" :disabled="!canApprove" @click="approvePreview">اعتماد التعديل</button>
            <button class="button button--secondary" type="button" @click="discardPreview">إلغاء المعاينة</button>
          </div>
        </section>
        <button v-else data-testid="approve-change" class="button button--primary hidden-approve" type="button" disabled>اعتماد التعديل</button>
      </aside>
    </main>

  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import BrandMark from '../components/BrandMark.vue'
import { api } from '../services/api'
import { roomLabelAr } from '../utils/roomLabels'

const route = useRoute()
const projectId = computed(() => String(route.params.id || 'new'))
const shortProjectId = computed(() => projectId.value.slice(0, 8))

const selectedRoom = ref('')
const selectedElement = ref('')
const wallOffset = ref('50')
const prompt = ref('')
const aiPlanning = ref(false)
const showComparison = ref(true)
const message = ref('اختر غرفة للبدء. النسخة المعتمدة محفوظة كما هي.')
const messageTone = ref('info')
const sessionState = ref(null)
const pendingPreview = ref(null)
const structuralReviewConfirmed = ref(false)
const draftScaleConfirmed = ref(false)
const draftGeometryConfirmed = ref(false)
const loading = ref(true)
const busy = ref(false)

const revision = computed(() => sessionState.value?.revision_number ?? 0)
const approvedGeometry = computed(() => sessionState.value?.geometry || null)
const approvedRooms = computed(() => approvedGeometry.value?.rooms || [])
const approvedWalls = computed(() => approvedGeometry.value?.walls || [])
const previewGeometry = computed(() => pendingPreview.value?.geometry || null)
const previewWalls = computed(() => previewGeometry.value?.walls || [])
const hasPreview = computed(() => Boolean(pendingPreview.value))
const scaleConfirmed = computed(() => Number(sessionState.value?.scale_confidence || 0) >= 0.8)
const geometryConfirmed = computed(() => Number(sessionState.value?.geometry_confidence || 0) >= 0.8)
const scalePercent = computed(() => Math.round(Number(sessionState.value?.scale_confidence || 0) * 100))
const selectedRoomLabel = computed(() => {
  const label = approvedRooms.value.find(room => room.id === selectedRoom.value)?.label
  return label ? roomLabelAr(label) : 'الغرفة'
})
const selectedWall = computed(() => {
  const wallId = selectedElement.value || pendingPreview.value?.operation?.wall_id
  return approvedWalls.value.find(wall => wall.id === wallId) || null
})
const selectedWallLabel = computed(() => selectedWall.value ? wallLabel(selectedWall.value) : 'الجدار المشترك')
const positiveRoomLabel = computed(() => {
  const roomId = selectedWall.value?.room_ids?.[0]
  const label = approvedRooms.value.find(room => room.id === roomId)?.label
  return label ? roomLabelAr(label) : 'الغرفة الأولى'
})
const previewDelta = computed(() => Number(pendingPreview.value?.operation?.offset_mm || 0) / 10)
const canApprove = computed(() => {
  if (!hasPreview.value || busy.value || !scaleConfirmed.value || !geometryConfirmed.value) return false
  return selectedWall.value?.structural_status !== 'unknown' || structuralReviewConfirmed.value
})
const affectedRoomComparisons = computed(() => {
  if (!selectedWall.value || !previewGeometry.value) return []
  const previewRooms = new Map(previewGeometry.value.rooms.map(room => [room.id, room]))
  return selectedWall.value.room_ids.map((roomId) => {
    const before = approvedRooms.value.find(room => room.id === roomId)
    const after = previewRooms.get(roomId)
    return {
      id: roomId,
      label: roomLabelAr(before?.label || roomId),
      before: Number(before?.area_m2 || 0),
      after: Number(after?.area_m2 || 0),
    }
  })
})
const planViewBox = computed(() => {
  const width = Number(approvedGeometry.value?.canvas?.width_mm || 1000)
  const height = Number(approvedGeometry.value?.canvas?.height_mm || 1000)
  const margin = Math.max(width, height) * 0.04
  return `${-margin} ${-margin} ${width + margin * 2} ${height + margin * 2}`
})
const labelGap = computed(() => Math.max(Number(approvedGeometry.value?.canvas?.height_mm || 1000) * 0.07, 140))
const labelStyle = computed(() => ({ fontSize: `${Math.max(Number(approvedGeometry.value?.canvas?.width_mm || 1000) / 42, 140)}px` }))
const areaStyle = computed(() => ({ fontSize: `${Math.max(Number(approvedGeometry.value?.canvas?.width_mm || 1000) / 52, 115)}px` }))

function setMessage(text, tone = 'info') {
  message.value = text
  messageTone.value = tone
}

function readableError(error, fallback) {
  const detail = error?.payload?.detail
  if (typeof detail === 'object' && detail?.message) return detail.message
  if (typeof error?.message === 'string') return error.message
  return fallback
}

function wallLine(wall) {
  if (wall.orientation === 'vertical') {
    return { x1: wall.coordinate_mm, y1: wall.start_mm, x2: wall.coordinate_mm, y2: wall.end_mm }
  }
  return { x1: wall.start_mm, y1: wall.coordinate_mm, x2: wall.end_mm, y2: wall.coordinate_mm }
}

function wallLabel(wall) {
  const roomNames = wall.room_ids
    .map(roomId => approvedRooms.value.find(room => room.id === roomId)?.label)
    .filter(Boolean)
    .map(roomLabelAr)
  return roomNames.length === 2 ? `الجدار بين ${roomNames[0]} و${roomNames[1]}` : 'جدار مشترك'
}

function selectRoom(room) {
  selectedRoom.value = room
  const canonicalLabel = approvedRooms.value.find(item => item.id === room)?.label
  const label = canonicalLabel ? roomLabelAr(canonicalLabel) : 'الغرفة'
  setMessage(`تم اختيار ${label}. اختر العنصر المطلوب.`)
}

async function loadEditor() {
  loading.value = true
  try {
    const state = await api.editor.getState(projectId.value)
    sessionState.value = state
    pendingPreview.value = state.pending_preview
    if (state.pending_preview?.operation?.wall_id) {
      selectedElement.value = state.pending_preview.operation.wall_id
    }
    setMessage('تم تحميل آخر نسخة معتمدة من الخادم.')
  } catch (error) {
    setMessage(readableError(error, 'تعذر تحميل المحرر.'), 'warning')
  } finally {
    loading.value = false
  }
}

onMounted(loadEditor)

function selectElement(element) {
  if (!selectedRoom.value) {
    setMessage('اختر الغرفة أولًا ثم اختر العنصر.', 'warning')
    return
  }
  selectedElement.value = element
  structuralReviewConfirmed.value = false
  setMessage(`تم اختيار ${selectedWallLabel.value}.`)
}

async function confirmDraft() {
  if (!draftScaleConfirmed.value || !draftGeometryConfirmed.value || busy.value) return
  busy.value = true
  try {
    sessionState.value = await api.editor.confirmDraft(projectId.value, {
      scale_confirmed: draftScaleConfirmed.value,
      geometry_confirmed: draftGeometryConfirmed.value,
    })
    pendingPreview.value = sessionState.value.pending_preview
    setMessage('تم تأكيد الرسم والمقياس لهذه الجلسة. ما زالت الحالة الإنشائية للجدران تحتاج مراجعة مستقلة.')
  } catch (error) {
    setMessage(readableError(error, 'تعذر حفظ تأكيد الرسم والمقياس.'), 'warning')
  } finally {
    busy.value = false
  }
}

async function requestPreview(value, label) {
  if (!sessionState.value || !selectedWall.value) return
  busy.value = true
  try {
    pendingPreview.value = await api.editor.createPreview(projectId.value, {
      base_revision_id: sessionState.value.revision_id,
      wall_id: selectedWall.value.id,
      offset_mm: Math.round(value * 10),
      label_ar: label,
    })
    structuralReviewConfirmed.value = false
    showComparison.value = true
    setMessage(`تم إنشاء معاينة محفوظة: ${label}. النسخة المعتمدة لم تتغير.`)
  } catch (error) {
    setMessage(readableError(error, 'تعذر إنشاء المعاينة.'), 'warning')
  } finally {
    busy.value = false
  }
}

async function createPreview() {
  const value = Number(wallOffset.value)
  if (!selectedRoom.value || !selectedWall.value) {
    setMessage('اختر الغرفة ثم الجدار المشترك قبل إنشاء المعاينة.', 'warning')
    return
  }
  if (!Number.isFinite(value) || value === 0 || value < -150 || value > 150) {
    setMessage('اكتب رقمًا من −150 إلى 150 سم. لم نغيّر القيمة التي أدخلتها.', 'warning')
    return
  }
  await requestPreview(value, `تحريك الجدار ${Math.abs(value)} سم`)
}

async function createPromptPreview() {
  const text = prompt.value.trim()
  if (!text) {
    setMessage('اكتب طلبًا قصيرًا أولًا.', 'warning')
    return
  }
  if (!selectedRoom.value || !selectedWall.value) {
    setMessage('حدد الغرفة والجدار المقصود على المخطط قبل تفسير الطلب.', 'warning')
    return
  }
  const requestedRevision = revision.value
  const requestedRevisionId = sessionState.value?.revision_id
  aiPlanning.value = true
  try {
    const intent = await api.editor.planIntent(projectId.value, {
      prompt: text,
      selection: {
        room_id: selectedRoom.value,
        element_id: selectedWall.value.id,
        element_type: 'wall',
      },
      revision: requestedRevision,
    })
    if (
      revision.value !== requestedRevision
      || sessionState.value?.revision_id !== requestedRevisionId
      || intent.base_revision !== requestedRevision
    ) {
      setMessage('تغيّرت النسخة المعتمدة أثناء فهم الطلب. أرسل الطلب مرة أخرى لإنشاء معاينة محدثة.', 'warning')
      return
    }
    if (intent.status !== 'ready') {
      setMessage(intent.clarification || intent.explanation || 'يحتاج الطلب إلى توضيح قبل إنشاء المعاينة.', 'warning')
      return
    }
    const operation = intent.operation
    const value = Number(operation?.delta_cm)
    if (operation?.kind !== 'move_wall' || operation?.target_id !== selectedWall.value.id) {
      setMessage('خطة الذكاء الاصطناعي لا تطابق العنصر المحدد، لذلك لم ننشئ معاينة.', 'warning')
      return
    }
    if (!Number.isFinite(value) || value === 0 || value < -150 || value > 150) {
      setMessage('القيمة المفهومة خارج المجال المسموح من −150 إلى 150 سم.', 'warning')
      return
    }
    wallOffset.value = String(value)
    await requestPreview(value, `طلب نصي: تحريك الجدار ${Math.abs(value)} سم`)
    if (intent.explanation) setMessage(`${intent.explanation} هذه معاينة فقط ولم تعتمد بعد.`)
  } catch (error) {
    setMessage(readableError(error, 'تعذر فهم الطلب حاليًا. جرّب مرة أخرى.'), 'warning')
  } finally {
    aiPlanning.value = false
  }
}

async function approvePreview() {
  if (!canApprove.value) return
  busy.value = true
  try {
    sessionState.value = await api.editor.approvePreview(
      projectId.value,
      pendingPreview.value.preview_id,
      { structural_review_confirmed: structuralReviewConfirmed.value },
    )
    pendingPreview.value = sessionState.value.pending_preview
    structuralReviewConfirmed.value = false
    setMessage('تم اعتماد التعديل وحفظ Revision جديدة. يمكنك التراجع فورًا.')
  } catch (error) {
    setMessage(readableError(error, 'تعذر اعتماد المعاينة.'), 'warning')
  } finally {
    busy.value = false
  }
}

async function discardPreview() {
  if (!pendingPreview.value || busy.value) return
  busy.value = true
  try {
    sessionState.value = await api.editor.discardPreview(projectId.value, pendingPreview.value.preview_id)
    pendingPreview.value = sessionState.value.pending_preview
    structuralReviewConfirmed.value = false
    setMessage('ألغينا المعاينة المحفوظة. النسخة المعتمدة لم تتغير.')
  } catch (error) {
    setMessage(readableError(error, 'تعذر إلغاء المعاينة.'), 'warning')
  } finally {
    busy.value = false
  }
}

async function undo() {
  if (!sessionState.value?.can_undo || busy.value) return
  busy.value = true
  try {
    sessionState.value = await api.editor.undo(projectId.value)
    pendingPreview.value = sessionState.value.pending_preview
    setMessage('تم التراجع عن آخر Revision محفوظة.')
  } catch (error) {
    setMessage(readableError(error, 'تعذر التراجع.'), 'warning')
  } finally {
    busy.value = false
  }
}

async function redo() {
  if (!sessionState.value?.can_redo || busy.value) return
  busy.value = true
  try {
    sessionState.value = await api.editor.redo(projectId.value)
    pendingPreview.value = sessionState.value.pending_preview
    setMessage('تمت إعادة Revision المحفوظة.')
  } catch (error) {
    setMessage(readableError(error, 'تعذرت الإعادة.'), 'warning')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.editor-page {
  min-height: 100vh;
  background: var(--emad-bg);
  color: var(--emad-ink);
}

.editor-header {
  display: flex;
  min-height: 4.5rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.7rem 1rem;
  border-bottom: 1px solid var(--emad-line);
  background: var(--emad-surface);
}

.editor-header__identity,
.editor-header__actions {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.editor-header h1,
.editor-header p,
.panel-heading h2,
.panel-heading p,
.canvas-toolbar h2 {
  margin: 0;
}

.editor-header h1 {
  font-size: 1rem;
  font-weight: 720;
}

.editor-header p {
  color: var(--emad-muted);
  font-size: 0.7rem;
}

.icon-button {
  display: inline-grid;
  width: 2.6rem;
  height: 2.6rem;
  place-items: center;
  border: 1px solid var(--emad-line);
  border-radius: 0.7rem;
  background: var(--emad-surface);
  color: var(--emad-ink-soft);
  text-decoration: none;
  cursor: pointer;
}

.editor-shell {
  display: grid;
  grid-template-columns: minmax(14rem, 17rem) minmax(31rem, 1fr) minmax(18rem, 22rem);
  gap: 0.8rem;
  min-height: calc(100vh - 4.5rem);
  padding: 0.8rem;
}

.editor-panel,
.canvas-column {
  min-width: 0;
}

.editor-panel {
  align-self: start;
  padding: 1rem;
  border: 1px solid var(--emad-line);
  border-radius: var(--emad-radius-lg);
  background: var(--emad-surface);
  box-shadow: var(--emad-shadow-sm);
}

.selection-panel,
.action-panel {
  position: sticky;
  top: 0.8rem;
  max-height: calc(100vh - 6.1rem);
  overflow-y: auto;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--emad-line);
}

.panel-step {
  display: grid;
  width: 1.8rem;
  height: 1.8rem;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
  font-size: 0.72rem;
  font-weight: 750;
}

.panel-heading h2,
.canvas-toolbar h2 {
  font-size: 0.9rem;
  font-weight: 720;
}

.panel-heading p {
  margin-top: 0.15rem;
  color: var(--emad-muted);
  font-size: 0.7rem;
}

.selection-path {
  display: flex;
  min-height: 2.7rem;
  align-items: center;
  gap: 0.45rem;
  margin-block: 0.8rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.65rem;
  background: var(--emad-surface-subtle);
  color: var(--emad-muted);
  font-size: 0.72rem;
}

.selection-path b {
  color: var(--emad-ink-soft);
}

.selection-path i {
  font-size: 0.55rem;
}

.element-group {
  margin-top: 1rem;
}

.element-group h3 {
  margin: 0 0 0.45rem;
  color: var(--emad-muted);
  font-size: 0.68rem;
  font-weight: 700;
}

.element-button {
  display: flex;
  width: 100%;
  min-height: 2.8rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.4rem;
  padding: 0.6rem 0.7rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.65rem;
  background: var(--emad-surface);
  color: var(--emad-ink-soft);
  font: inherit;
  font-size: 0.76rem;
  text-align: right;
  cursor: pointer;
}

.element-button:hover,
.element-button--selected {
  border-color: rgba(23, 107, 91, 0.35);
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
}

.element-button span {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.element-button small {
  color: var(--emad-muted);
}

.panel-tip {
  margin: 1rem 0 0;
  color: var(--emad-muted);
  font-size: 0.68rem;
}

.canvas-column {
  display: grid;
  align-content: start;
  gap: 0.65rem;
}

.canvas-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--emad-line);
  border-radius: var(--emad-radius-lg);
  background: var(--emad-surface);
}

.canvas-toolbar h2 {
  margin-top: 0.25rem;
}

.canvas-wrap {
  position: relative;
  display: grid;
  min-height: 35rem;
  place-items: center;
  overflow: hidden;
  border: 1px solid var(--emad-line);
  border-radius: var(--emad-radius-lg);
  background-color: #eceeea;
  background-image: linear-gradient(rgba(31, 39, 34, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(31, 39, 34, 0.04) 1px, transparent 1px);
  background-size: 22px 22px;
}

.canvas-wrap--preview {
  border-color: rgba(47, 111, 159, 0.35);
}

.canvas-wrap svg {
  width: min(100%, 64rem);
  height: auto;
  color: var(--emad-preview);
}

.plan-outline {
  fill: var(--emad-surface);
  stroke: #26352f;
  stroke-width: 13;
}

.room-fill {
  fill: rgba(255, 254, 250, 0.9);
  stroke: transparent;
  cursor: pointer;
}

.room-fill:hover,
.room-fill--selected {
  fill: rgba(23, 107, 91, 0.08);
}

.current-wall {
  stroke: #26352f;
  stroke-width: 14;
  cursor: pointer;
}

.current-wall:hover,
.current-wall--selected {
  stroke: var(--emad-accent);
  stroke-width: 18;
}

.window-line {
  stroke: #2f6f9f;
  stroke-width: 15;
  cursor: pointer;
}

.door-line {
  fill: none;
  stroke: #795e39;
  stroke-width: 8;
  cursor: pointer;
}

.building-element--selected {
  filter: drop-shadow(0 0 4px rgba(23, 107, 91, 0.55));
  stroke: var(--emad-accent);
}

.proposal-wall {
  stroke: var(--emad-preview);
  stroke-width: 12;
  stroke-dasharray: 17 11;
}

.movement-arrow {
  fill: none;
  stroke: var(--emad-preview);
  stroke-width: 5;
}

.room-label,
.room-area {
  fill: var(--emad-ink-soft);
  text-anchor: middle;
  pointer-events: none;
}

.room-label {
  font-size: 24px;
  font-weight: 700;
}

.room-area {
  fill: var(--emad-muted);
  font-size: 20px;
}

.canvas-legend {
  position: absolute;
  bottom: 0.8rem;
  left: 0.8rem;
  display: flex;
  gap: 0.75rem;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.6rem;
  background: var(--emad-surface);
  color: var(--emad-muted);
  font-size: 0.66rem;
}

.canvas-legend span {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.legend-current,
.legend-proposal {
  display: inline-block;
  width: 1.4rem;
  border-top: 3px solid #26352f;
}

.legend-proposal {
  border-top: 3px dashed var(--emad-preview);
}

.editor-message {
  display: flex;
  min-height: 2.9rem;
  align-items: center;
  gap: 0.55rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.75rem;
  background: var(--emad-surface);
  color: var(--emad-ink-soft);
  font-size: 0.75rem;
}

.editor-message--warning {
  border-color: rgba(129, 85, 10, 0.2);
  background: var(--emad-warning-soft);
  color: var(--emad-warning);
}

.action-section {
  display: grid;
  gap: 0.65rem;
  margin-top: 0.9rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--emad-line);
}

.action-section label {
  color: var(--emad-ink-soft);
  font-size: 0.76rem;
  font-weight: 700;
}

.action-section p {
  margin: 0;
  color: var(--emad-muted);
  font-size: 0.68rem;
}

.number-field {
  display: grid;
  grid-template-columns: 1fr auto;
  overflow: hidden;
  border: 1px solid var(--emad-line-strong);
  border-radius: 0.7rem;
}

.number-field input,
.prompt-section textarea {
  min-width: 0;
  border: 0;
  background: var(--emad-surface);
  color: var(--emad-ink);
  font: inherit;
  outline: 0;
}

.number-field input {
  min-height: 3rem;
  padding: 0.65rem 0.75rem;
}

.number-field span {
  display: grid;
  min-width: 3rem;
  place-items: center;
  border-right: 1px solid var(--emad-line);
  background: var(--emad-surface-subtle);
  color: var(--emad-muted);
  font-size: 0.75rem;
}

.prompt-section textarea {
  min-height: 5.5rem;
  padding: 0.7rem;
  border: 1px solid var(--emad-line-strong);
  border-radius: 0.7rem;
  resize: vertical;
}

.empty-action {
  display: grid;
  min-height: 9rem;
  place-items: center;
  align-content: center;
  gap: 0.3rem;
  margin-top: 0.9rem;
  padding: 1rem;
  border-radius: 0.75rem;
  background: var(--emad-surface-subtle);
  color: var(--emad-muted);
  text-align: center;
}

.empty-action strong {
  color: var(--emad-ink-soft);
  font-size: 0.78rem;
}

.empty-action p {
  margin: 0;
  font-size: 0.68rem;
}

.draft-confirmation {
  display: grid;
  gap: 0.7rem;
  margin-top: 0.9rem;
  padding: 0.85rem;
  border: 1px solid rgba(129, 85, 10, 0.24);
  border-radius: 0.75rem;
  background: var(--emad-warning-soft);
}

.draft-confirmation h3,
.draft-confirmation p {
  margin: 0.35rem 0 0;
}

.draft-confirmation h3 {
  color: var(--emad-warning);
  font-size: 0.82rem;
}

.draft-confirmation p,
.draft-confirmation label,
.structural-confirmation {
  color: var(--emad-ink-soft);
  font-size: 0.69rem;
  line-height: 1.65;
}

.draft-confirmation label,
.structural-confirmation {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
}

.draft-confirmation input,
.structural-confirmation input {
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
  margin-top: 0.15rem;
  accent-color: var(--emad-accent);
}

.structural-confirmation {
  margin: 0.7rem 0;
  padding: 0.65rem;
  border-radius: 0.6rem;
  background: rgba(255, 255, 255, 0.55);
}

.preview-panel {
  margin-top: 0.9rem;
  padding: 0.85rem;
  border: 1px solid rgba(47, 111, 159, 0.25);
  border-radius: 0.75rem;
  background: var(--emad-preview-soft);
}

.preview-panel__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  color: var(--emad-preview);
  font-size: 0.76rem;
}

.preview-panel ul {
  margin: 0.75rem 0;
  padding-right: 1.1rem;
  color: var(--emad-ink-soft);
  font-size: 0.7rem;
  line-height: 1.9;
}

.preview-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.hidden-approve {
  width: 100%;
  margin-top: 0.9rem;
}

.modal-backdrop {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(21, 30, 26, 0.55);
}

.planner-dialog {
  width: min(100%, 52rem);
  padding: 1.25rem;
  border: 1px solid var(--emad-line);
  border-radius: 1rem;
  background: var(--emad-surface);
  box-shadow: var(--emad-shadow-lg);
}

.planner-dialog > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.planner-dialog h2,
.planner-dialog p {
  margin: 0;
}

.planner-dialog h2 {
  font-size: 1.1rem;
}

.planner-dialog p {
  margin-top: 0.3rem;
  color: var(--emad-muted);
  font-size: 0.75rem;
}

.candidate-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.7rem;
  margin-top: 1rem;
}

.candidate {
  display: grid;
  min-height: 12rem;
  align-content: start;
  gap: 0.5rem;
  padding: 1rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.8rem;
  background: var(--emad-surface-subtle);
  color: var(--emad-ink-soft);
  font: inherit;
  text-align: right;
  cursor: pointer;
}

.candidate:hover {
  border-color: rgba(23, 107, 91, 0.4);
  background: var(--emad-accent-soft);
}

.candidate .badge {
  justify-self: start;
}

.candidate strong {
  font-size: 0.88rem;
}

.candidate p,
.candidate small {
  color: var(--emad-muted);
  font-size: 0.7rem;
}

@media (max-width: 1100px) {
  .editor-shell {
    grid-template-columns: minmax(13rem, 15rem) minmax(28rem, 1fr);
  }

  .action-panel {
    position: static;
    grid-column: 1 / -1;
    max-height: none;
  }
}

@media (max-width: 760px) {
  .editor-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .editor-header__actions {
    width: 100%;
    overflow-x: auto;
  }

  .editor-shell {
    grid-template-columns: 1fr;
  }

  .selection-panel,
  .action-panel {
    position: static;
    max-height: none;
  }

  .canvas-column {
    grid-row: 2;
  }

  .canvas-wrap {
    min-height: 22rem;
  }

  .candidate-list,
  .preview-actions {
    grid-template-columns: 1fr;
  }
}
</style>
