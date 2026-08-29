import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { uploadProject } = vi.hoisted(() => ({ uploadProject: vi.fn() }))

vi.mock('../services/api', () => ({
  api: { projects: { upload: uploadProject } },
}))

import { useAuthStore } from '../stores/auth'
import HomeView from './HomeView.vue'

function mountHome({ authenticated = false } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (authenticated) {
    useAuthStore().setAuth('token', {
      id: 1,
      full_name: 'فهد التجربة',
      email: 'fahad@example.com',
      role: 'customer',
    })
  }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: HomeView },
      { path: '/projects', component: { template: '<div />' } },
      { path: '/projects/:id', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
      { path: '/register', component: { template: '<div />' } },
      { path: '/profile', component: { template: '<div />' } },
      { path: '/admin', component: { template: '<div />' } },
    ],
  })

  const wrapper = mount(HomeView, { global: { plugins: [pinia, router] } })
  return { wrapper, router }
}

describe('HomeView', () => {
  beforeEach(() => uploadProject.mockReset())

  it('frames upload as a clear homeowner task with an honest preliminary-results notice', () => {
    const { wrapper } = mountHome()

    expect(wrapper.get('h1').text()).toContain('ابدأ بصورة مخطط منزلك')
    expect(wrapper.text()).toContain('PDF أو PNG أو JPG')
    expect(wrapper.text()).toContain('النتائج إرشادية أولية')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('opens the database project id returned by upload instead of the task id', async () => {
    uploadProject.mockResolvedValue({
      project_id: 42,
      task_id: 'analysis-task-uuid',
      image_url: '/uploads/plan.png',
      status: 'processing',
    })
    const { wrapper, router } = mountHome({ authenticated: true })
    const input = wrapper.get('input[type="file"]')
    const file = new File(['plan'], 'plan.pdf', { type: 'application/pdf' })
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')
    await wrapper.get('button[type="submit"]').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/projects/42')
  })
})
