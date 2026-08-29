import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const editorApi = vi.hoisted(() => ({
  getState: vi.fn(),
  createPreview: vi.fn(),
  approvePreview: vi.fn(),
  confirmDraft: vi.fn(),
  discardPreview: vi.fn(),
  undo: vi.fn(),
  redo: vi.fn(),
  planIntent: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: { editor: editorApi },
}))

import EditorView from './EditorView.vue'

const baseGeometry = {
  schema_version: 'emad.rect-geometry.v1',
  canvas: { width_mm: 8000, height_mm: 3000 },
  scale_confidence: 0.96,
  geometry_confidence: 0.9,
  rooms: [
    { id: 'room_1', label: 'مكتب المنزل', x_mm: 0, y_mm: 0, width_mm: 4000, height_mm: 3000, area_m2: 12 },
    { id: 'room_2', label: 'غرفة النوم', x_mm: 4000, y_mm: 0, width_mm: 4000, height_mm: 3000, area_m2: 12 },
  ],
  walls: [
    {
      id: 'wall:room_1:room_2:v',
      orientation: 'vertical',
      coordinate_mm: 4000,
      start_mm: 0,
      end_mm: 3000,
      room_ids: ['room_1', 'room_2'],
      structural_status: 'unknown',
    },
  ],
}

function editorState(overrides = {}) {
  return {
    project_id: 7,
    revision_id: 'a'.repeat(64),
    revision_number: 3,
    geometry: baseGeometry,
    scale_confidence: 0.96,
    geometry_confidence: 0.9,
    can_undo: true,
    can_redo: false,
    pending_preview: null,
    ...overrides,
  }
}

async function mountEditor() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/projects/:id', component: { template: '<div />' } },
      { path: '/projects/:id/editor', component: EditorView },
      { path: '/projects', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
      { path: '/register', component: { template: '<div />' } },
      { path: '/profile', component: { template: '<div />' } },
      { path: '/admin', component: { template: '<div />' } },
    ],
  })
  await router.push('/projects/7/editor')
  await router.isReady()
  return mount(EditorView, { global: { plugins: [createPinia(), router] } })
}

describe('EditorView', () => {
  beforeEach(() => {
    Object.values(editorApi).forEach(mock => mock.mockReset())
    editorApi.getState.mockResolvedValue(editorState())
  })

  it('loads and renders the persisted project geometry instead of demo rooms', async () => {
    const wrapper = await mountEditor()
    await flushPromises()

    expect(editorApi.getState).toHaveBeenCalledWith('7')
    expect(wrapper.text()).toContain('النسخة المعتمدة 3')
    expect(wrapper.text()).toContain('مكتب المنزل')
  })

  it('renders canonical room labels in Arabic without changing stored geometry labels', async () => {
    editorApi.getState.mockResolvedValue(editorState({
      geometry: {
        ...baseGeometry,
        rooms: [
          { ...baseGeometry.rooms[0], label: 'Bedroom' },
          { ...baseGeometry.rooms[1], label: 'Bathroom' },
        ],
      },
    }))

    const wrapper = await mountEditor()
    await flushPromises()

    expect(wrapper.text()).toContain('غرفة نوم')
    expect(wrapper.text()).toContain('دورة مياه')
    expect(wrapper.text()).not.toContain('Bedroom')
    expect(wrapper.text()).not.toContain('Bathroom')
  })

  it('requires explicit scale and drawing confirmation for a preliminary editor session', async () => {
    editorApi.getState.mockResolvedValue(editorState({
      scale_confidence: 0.45,
      geometry_confidence: 0.65,
    }))
    editorApi.confirmDraft.mockResolvedValue(editorState({
      scale_confidence: 1,
      geometry_confidence: 1,
    }))
    const wrapper = await mountEditor()
    await flushPromises()

    expect(wrapper.text()).toContain('راجع الرسم والمقياس')
    expect(wrapper.get('[data-testid="confirm-draft"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="confirm-scale"]').setValue(true)
    await wrapper.get('[data-testid="confirm-geometry"]').setValue(true)
    await wrapper.get('[data-testid="confirm-draft"]').trigger('click')
    await flushPromises()

    expect(editorApi.confirmDraft).toHaveBeenCalledWith('7', {
      scale_confirmed: true,
      geometry_confirmed: true,
    })
    expect(wrapper.text()).not.toContain('راجع الرسم والمقياس')
  })

  it('creates and renders a persisted wall preview without changing the approved revision', async () => {
    editorApi.discardPreview.mockResolvedValue(editorState())
    editorApi.createPreview.mockResolvedValue({
      preview_id: 4,
      status: 'pending',
      base_revision_id: 'a'.repeat(64),
      label_ar: 'تحريك الجدار 50 سم',
      operation: { kind: 'move_wall', wall_id: 'wall:room_1:room_2:v', offset_mm: 500 },
      geometry: {
        ...baseGeometry,
        rooms: [
          { ...baseGeometry.rooms[0], width_mm: 4500, area_m2: 13.5 },
          { ...baseGeometry.rooms[1], x_mm: 4500, width_mm: 3500, area_m2: 10.5 },
        ],
        walls: [{ ...baseGeometry.walls[0], coordinate_mm: 4500 }],
      },
    })
    const wrapper = await mountEditor()
    await flushPromises()

    expect(wrapper.get('h1').text()).toContain('تعديل المخطط')
    expect(wrapper.get('[data-testid="approve-change"]').attributes('disabled')).toBeDefined()

    await wrapper.get('[data-testid="room-room_1"]').trigger('click')
    await wrapper.get('[data-testid="wall-option"]').trigger('click')
    await wrapper.get('[data-testid="wall-offset"]').setValue('50')
    await wrapper.get('[data-testid="create-preview"]').trigger('click')
    await flushPromises()

    expect(editorApi.createPreview).toHaveBeenCalledWith('7', {
      base_revision_id: 'a'.repeat(64),
      wall_id: 'wall:room_1:room_2:v',
      offset_mm: 500,
      label_ar: 'تحريك الجدار 50 سم',
    })
    expect(wrapper.get('[data-testid="preview-status"]').text()).toContain('لم تعتمد')
    expect(wrapper.get('[data-testid="approve-change"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="structural-review"]').setValue(true)
    expect(wrapper.get('[data-testid="approve-change"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('12.0 ← 13.5 م²')

    const discardButton = wrapper.findAll('button').find(button => button.text().includes('إلغاء المعاينة'))
    await discardButton.trigger('click')
    await flushPromises()
    expect(editorApi.discardPreview).toHaveBeenCalledWith('7', 4)
    expect(wrapper.find('[data-testid="preview-status"]').exists()).toBe(false)
  })

  it('approves a persisted revision then uses backend undo and redo', async () => {
    const changedGeometry = {
      ...baseGeometry,
      rooms: [
        { ...baseGeometry.rooms[0], width_mm: 4500, area_m2: 13.5 },
        { ...baseGeometry.rooms[1], x_mm: 4500, width_mm: 3500, area_m2: 10.5 },
      ],
      walls: [{ ...baseGeometry.walls[0], coordinate_mm: 4500 }],
    }
    editorApi.createPreview.mockResolvedValue({
      preview_id: 4,
      status: 'pending',
      base_revision_id: 'a'.repeat(64),
      label_ar: 'تحريك الجدار 50 سم',
      operation: { kind: 'move_wall', wall_id: 'wall:room_1:room_2:v', offset_mm: 500 },
      geometry: changedGeometry,
    })
    const approvedState = editorState({
      revision_id: 'c'.repeat(64),
      revision_number: 4,
      geometry: changedGeometry,
      can_undo: true,
      can_redo: false,
    })
    editorApi.approvePreview.mockResolvedValue(approvedState)
    editorApi.undo.mockResolvedValue(editorState({ can_undo: true, can_redo: true }))
    editorApi.redo.mockResolvedValue(approvedState)
    const wrapper = await mountEditor()
    await flushPromises()

    await wrapper.get('[data-testid="room-room_1"]').trigger('click')
    await wrapper.get('[data-testid="wall-option"]').trigger('click')
    await wrapper.get('[data-testid="create-preview"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="structural-review"]').setValue(true)
    await wrapper.get('[data-testid="approve-change"]').trigger('click')
    await flushPromises()

    expect(editorApi.approvePreview).toHaveBeenCalledWith('7', 4, { structural_review_confirmed: true })
    expect(wrapper.text()).toContain('النسخة المعتمدة 4')

    await wrapper.get('[data-testid="undo-change"]').trigger('click')
    await flushPromises()
    expect(editorApi.undo).toHaveBeenCalledWith('7')
    expect(wrapper.text()).toContain('النسخة المعتمدة 3')

    await wrapper.get('[data-testid="redo-change"]').trigger('click')
    await flushPromises()
    expect(editorApi.redo).toHaveBeenCalledWith('7')
    expect(wrapper.text()).toContain('النسخة المعتمدة 4')
  })

  it('turns a typed AI edit intent into an unapproved preview', async () => {
    editorApi.planIntent.mockResolvedValue({
      status: 'ready',
      base_revision: 3,
      operation: {
        kind: 'move_wall',
        target_id: 'wall:room_1:room_2:v',
        delta_cm: 40,
      },
      explanation: 'تحريك الجدار المحدد 40 سم.',
      clarification: null,
      warnings: [],
    })
    editorApi.createPreview.mockResolvedValue({
      preview_id: 5,
      status: 'pending',
      base_revision_id: 'a'.repeat(64),
      label_ar: 'طلب نصي: تحريك الجدار 40 سم',
      operation: { kind: 'move_wall', wall_id: 'wall:room_1:room_2:v', offset_mm: 400 },
      geometry: {
        ...baseGeometry,
        rooms: [
          { ...baseGeometry.rooms[0], width_mm: 4400, area_m2: 13.2 },
          { ...baseGeometry.rooms[1], x_mm: 4400, width_mm: 3600, area_m2: 10.8 },
        ],
        walls: [{ ...baseGeometry.walls[0], coordinate_mm: 4400 }],
      },
    })
    const wrapper = await mountEditor()
    await flushPromises()

    await wrapper.get('[data-testid="room-room_1"]').trigger('click')
    await wrapper.get('[data-testid="wall-option"]').trigger('click')
    await wrapper.get('#edit-prompt').setValue('حرّك الجدار 40 سم نحو غرفة النوم')
    await wrapper.get('[data-testid="ai-preview"]').trigger('click')
    await flushPromises()

    expect(editorApi.planIntent).toHaveBeenCalledWith('7', {
      prompt: 'حرّك الجدار 40 سم نحو غرفة النوم',
      selection: {
        room_id: 'room_1',
        element_id: 'wall:room_1:room_2:v',
        element_type: 'wall',
      },
      revision: 3,
    })
    expect(editorApi.createPreview).toHaveBeenCalledWith('7', expect.objectContaining({
      base_revision_id: 'a'.repeat(64),
      wall_id: 'wall:room_1:room_2:v',
      offset_mm: 400,
    }))
    expect(wrapper.get('[data-testid="preview-status"]').text()).toContain('لم تعتمد')
    expect(wrapper.get('[data-testid="preview-status"]').text()).toContain('40 سم')
  })

  it('ignores an AI intent when the approved revision changes while it is loading', async () => {
    let resolveIntent
    editorApi.planIntent.mockReturnValue(new Promise((resolve) => { resolveIntent = resolve }))
    editorApi.undo.mockResolvedValue(editorState({
      revision_id: 'b'.repeat(64),
      revision_number: 2,
      can_undo: false,
      can_redo: true,
    }))
    const wrapper = await mountEditor()
    await flushPromises()

    await wrapper.get('[data-testid="room-room_1"]').trigger('click')
    await wrapper.get('[data-testid="wall-option"]').trigger('click')
    await wrapper.get('#edit-prompt').setValue('حرّك الجدار 40 سم')
    await wrapper.get('[data-testid="ai-preview"]').trigger('click')

    await wrapper.get('[data-testid="undo-change"]').trigger('click')
    await flushPromises()

    resolveIntent({
      status: 'ready',
      base_revision: 3,
      operation: {
        kind: 'move_wall',
        target_id: 'wall:room_1:room_2:v',
        delta_cm: 40,
      },
      explanation: 'رد قديم.',
      clarification: null,
      warnings: [],
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="preview-status"]').exists()).toBe(false)
    expect(editorApi.createPreview).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('تغيّرت النسخة المعتمدة')
  })
})
