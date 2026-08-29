import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../services/api', () => ({
  api: { auth: { me: vi.fn() } },
}))

import ProfileView from './ProfileView.vue'

describe('ProfileView', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('auth_token', 'token-1')
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      full_name: 'فهد',
      email: 'fahad@example.com',
      role: 'customer',
      account_type: 'personal',
      is_active: true,
      plans_count: 2,
      created_at: '2026-08-01T10:00:00Z',
    }))
  })

  it('clears the session and returns home on logout', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/profile', component: ProfileView },
        { path: '/', component: { template: '<div />' } },
        { path: '/projects', component: { template: '<div />' } },
        { path: '/login', component: { template: '<div />' } },
      ],
    })
    await router.push('/profile')
    await router.isReady()
    const wrapper = mount(ProfileView, {
      global: {
        plugins: [createPinia(), router],
        stubs: { AppHeader: true },
      },
    })

    await wrapper.get('[data-testid="logout"]').trigger('click')
    await flushPromises()

    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(router.currentRoute.value.fullPath).toBe('/')
  })
})
