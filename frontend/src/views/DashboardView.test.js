import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { getProject, getReport, downloadProjectReport } = vi.hoisted(() => ({
  getProject: vi.fn(),
  getReport: vi.fn(),
  downloadProjectReport: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: { projects: { get: getProject, report: getReport } },
}))
vi.mock('../utils/projectReport', () => ({ downloadProjectReport }))

import DashboardView from './DashboardView.vue'

describe('DashboardView', () => {
  beforeEach(() => {
    getProject.mockReset()
    getReport.mockReset()
    downloadProjectReport.mockReset()
  })

  afterEach(() => vi.useRealTimers())

  it('shows non-compliant detections as potential issues with an editor path', async () => {
    getProject.mockResolvedValue({
      id: 7,
      task_id: 'task-7',
      title: 'مخطط الدور الأرضي',
      status: 'completed',
      original_image_url: '/uploads/task-7.png',
      analyzed_image_url: '/uploads/task-7_analyzed.jpg',
      compliance_score: 72,
      rooms_count: 1,
      violations_count: 1,
      rooms_data: [
        {
          id: 'room-1',
          type: 'Bedroom',
          isCompliant: false,
          metrics: { area: 8.5, minDim: 2.4 },
          ragReason: 'المساحة المرصودة أقل من القيمة المرجعية.',
          reference: 'SBC 1101 — يحتاج تحقق من الصفحة والبند',
        },
      ],
      created_at: '2026-08-01T10:00:00Z',
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/projects/:id', component: DashboardView },
        { path: '/projects/:id/editor', component: { template: '<div />' } },
        { path: '/projects', component: { template: '<div />' } },
      ],
    })
    await router.push('/projects/7')
    await router.isReady()
    const wrapper = mount(DashboardView, {
      global: {
        plugins: [createPinia(), router],
        stubs: { AppHeader: true },
      },
    })
    await flushPromises()

    expect(getProject).toHaveBeenCalledWith('7')
    expect(wrapper.text()).toContain('مخطط الدور الأرضي')
    expect(wrapper.text()).toContain('مشكلة محتملة')
    expect(wrapper.text()).not.toContain('مخالفة مؤكدة')
    expect(wrapper.get('a[href="/projects/7/editor"]').exists()).toBe(true)
  })

  it('downloads a report built from the current approved revision', async () => {
    getProject.mockResolvedValue({
      id: 7,
      title: 'مخطط الدور الأرضي',
      status: 'completed',
      rooms_data: [],
    })
    const report = {
      project: { id: 7, title: 'مخطط الدور الأرضي' },
      revision: { number: 2 },
      rooms: [],
      findings: [],
    }
    getReport.mockResolvedValue(report)
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/projects/:id', component: DashboardView },
        { path: '/projects/:id/editor', component: { template: '<div />' } },
        { path: '/projects', component: { template: '<div />' } },
      ],
    })
    await router.push('/projects/7')
    await router.isReady()
    const wrapper = mount(DashboardView, {
      global: { plugins: [createPinia(), router], stubs: { AppHeader: true } },
    })
    await flushPromises()

    await wrapper.get('[data-testid="download-report"]').trigger('click')
    await flushPromises()

    expect(getReport).toHaveBeenCalledWith(7)
    expect(downloadProjectReport).toHaveBeenCalledWith(report)
    expect(wrapper.text()).toContain('تم تنزيل تقرير النسخة المعتمدة 2')
  })

  it('polls processing projects until a final status is available', async () => {
    vi.useFakeTimers()
    getProject
      .mockResolvedValueOnce({ id: 7, title: 'قيد التحليل', status: 'processing', rooms_data: [] })
      .mockResolvedValueOnce({ id: 7, title: 'قيد التحليل', status: 'completed', rooms_data: [] })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/projects/:id', component: DashboardView },
        { path: '/projects/:id/editor', component: { template: '<div />' } },
        { path: '/projects', component: { template: '<div />' } },
      ],
    })
    await router.push('/projects/7')
    await router.isReady()
    const wrapper = mount(DashboardView, {
      global: { plugins: [createPinia(), router], stubs: { AppHeader: true } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('التحليل ما زال قيد المعالجة')
    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()

    expect(getProject).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('حالة المراجعة الأولية')
    wrapper.unmount()
  })

  it('shows the persisted pipeline failure instead of a misleading empty result', async () => {
    getProject.mockResolvedValue({
      id: 7,
      title: 'مخطط غير مقروء',
      status: 'failed',
      rooms_data: [],
      analysis_error_code: 'room_detection_empty',
      analysis_error_message: 'لم يتمكن النظام من اكتشاف غرف قابلة للتحليل في الملف المرفوع.',
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/projects/:id', component: DashboardView },
        { path: '/projects/:id/editor', component: { template: '<div />' } },
        { path: '/projects', component: { template: '<div />' } },
      ],
    })
    await router.push('/projects/7')
    await router.isReady()
    const wrapper = mount(DashboardView, {
      global: { plugins: [createPinia(), router], stubs: { AppHeader: true } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('لم يتمكن النظام من اكتشاف غرف قابلة للتحليل')
    expect(wrapper.text()).not.toContain('حالة المراجعة الأولية')
    expect(wrapper.find('a[href="/projects/7/editor"]').exists()).toBe(false)
  })
})
