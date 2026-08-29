import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { login } = vi.hoisted(() => ({ login: vi.fn() }))

vi.mock('../../services/api', () => ({
  api: { auth: { login } },
}))

import LoginView from './LoginView.vue'

describe('LoginView', () => {
  beforeEach(() => {
    localStorage.clear()
    login.mockReset()
  })

  it('submits credentials and returns the user to the requested project', async () => {
    login.mockResolvedValue({
      access_token: 'token-1',
      user: {
        id: 1,
        full_name: 'فهد',
        email: 'fahad@example.com',
        role: 'customer',
      },
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/login', component: LoginView },
        { path: '/register', component: { template: '<div />' } },
        { path: '/projects/:id', component: { template: '<div />' } },
        { path: '/', component: { template: '<div />' } },
      ],
    })
    await router.push('/login?redirect=/projects/task-1')
    await router.isReady()
    const wrapper = mount(LoginView, {
      global: { plugins: [createPinia(), router] },
    })

    await wrapper.get('input[type="email"]').setValue('fahad@example.com')
    await wrapper.get('input[type="password"]').setValue('secret123')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(login).toHaveBeenCalledWith({
      email: 'fahad@example.com',
      password: 'secret123',
    })
    expect(localStorage.getItem('auth_token')).toBe('token-1')
    expect(router.currentRoute.value.fullPath).toBe('/projects/task-1')
  })
})
