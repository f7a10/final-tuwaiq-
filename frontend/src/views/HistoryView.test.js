import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { listProjects } = vi.hoisted(() => ({ listProjects: vi.fn() }))

vi.mock('../services/api', () => ({
  api: { projects: { list: listProjects } },
}))

import { useAuthStore } from '../stores/auth'
import HistoryView from './HistoryView.vue'

async function mountProjects() {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().setAuth('token', {
    id: 1,
    full_name: 'فهد التجربة',
    email: 'fahad@example.com',
    role: 'customer',
  })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/projects', component: HistoryView },
      { path: '/projects/:id', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
      { path: '/register', component: { template: '<div />' } },
      { path: '/profile', component: { template: '<div />' } },
      { path: '/admin', component: { template: '<div />' } },
    ],
  })
  await router.push('/projects')
  await router.isReady()
  const wrapper = mount(HistoryView, { global: { plugins: [pinia, router] } })
  return { wrapper, router }
}

describe('HistoryView', () => {
  beforeEach(() => {
    listProjects.mockReset()
    listProjects.mockResolvedValue({ projects: [], total: 0 })
  })

  it('shows a useful empty project state without invented statistics', async () => {
    const { wrapper } = await mountProjects()
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('مشاريعي')
    expect(wrapper.text()).toContain('لا توجد مشاريع بعد')
    expect(wrapper.text()).toContain('رفع أول مخطط')
    expect(wrapper.text()).not.toContain('إجمالي المشاريع')
  })

  it('opens a project by its database id instead of its analysis task id', async () => {
    listProjects.mockResolvedValue({
      projects: [{
        id: 7,
        task_id: 'analysis-task-uuid',
        title: 'منزل الاختبار',
        status: 'completed',
        rooms_count: 2,
      }],
      total: 1,
    })
    const { wrapper, router } = await mountProjects()
    await flushPromises()

    await wrapper.get('.project-preview').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/projects/7')
  })
})
