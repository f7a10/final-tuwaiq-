import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { register } = vi.hoisted(() => ({ register: vi.fn() }))

vi.mock('../../services/api', () => ({
  api: { auth: { register } },
}))

import RegisterView from './RegisterView.vue'

describe('RegisterView', () => {
  beforeEach(() => register.mockReset())

  it('creates a personal account and preserves the requested destination', async () => {
    register.mockResolvedValue({ user_id: 9 })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/register', component: RegisterView },
        { path: '/login', component: { template: '<div />' } },
        { path: '/', component: { template: '<div />' } },
      ],
    })
    await router.push('/register?redirect=/projects/task-1')
    await router.isReady()
    const wrapper = mount(RegisterView, { global: { plugins: [router] } })

    await wrapper.get('input[name="full_name"]').setValue('فهد')
    await wrapper.get('input[type="email"]').setValue('fahad@example.com')
    await wrapper.get('input[name="password"]').setValue('secret123')
    await wrapper.get('input[name="confirm_password"]').setValue('secret123')
    await wrapper.get('input[type="checkbox"]').setValue(true)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(register).toHaveBeenCalledWith({
      full_name: 'فهد',
      email: 'fahad@example.com',
      password: 'secret123',
      account_type: 'personal',
    })
    expect(router.currentRoute.value.fullPath).toBe('/login?redirect=/projects/task-1')
  })
})
