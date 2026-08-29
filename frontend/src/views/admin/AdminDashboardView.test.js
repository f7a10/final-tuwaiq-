import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { listUsers } = vi.hoisted(() => ({ listUsers: vi.fn() }))

vi.mock('../../services/api', () => ({
  api: { admin: { users: { list: listUsers } } },
}))

import AdminDashboardView from './AdminDashboardView.vue'

describe('AdminDashboardView', () => {
  beforeEach(() => listUsers.mockReset())

  it('renders users returned by the admin API instead of seed data', async () => {
    listUsers.mockResolvedValue([
      {
        id: 11,
        name: 'مستخدم حقيقي',
        email: 'real@example.com',
        role: 'customer',
        plansCount: 4,
        status: 'active',
      },
    ])
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/admin', component: AdminDashboardView },
        { path: '/', component: { template: '<div />' } },
        { path: '/projects', component: { template: '<div />' } },
      ],
    })
    await router.push('/admin')
    await router.isReady()
    const wrapper = mount(AdminDashboardView, {
      global: {
        plugins: [createPinia(), router],
        stubs: { AppHeader: true },
      },
    })
    await flushPromises()

    expect(listUsers).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('مستخدم حقيقي')
    expect(wrapper.text()).toContain('real@example.com')
    expect(wrapper.text()).not.toContain('سارة الأحمد')
  })
})
