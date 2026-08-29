import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { fetchMe } = vi.hoisted(() => ({ fetchMe: vi.fn() }))

vi.mock('../services/api', () => ({
  api: { auth: { me: fetchMe } },
}))

import { useAuthStore } from './auth'

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    fetchMe.mockReset()
    setActivePinia(createPinia())
  })

  it('refreshes the stored user from the authenticated API', async () => {
    const store = useAuthStore()
    store.setAuth('token-1', {
      id: 1,
      full_name: 'اسم قديم',
      email: 'old@example.com',
      role: 'customer',
    })
    fetchMe.mockResolvedValue({
      id: 1,
      full_name: 'الاسم المحدث',
      email: 'new@example.com',
      role: 'customer',
      plans_count: 3,
    })

    const user = await store.fetchCurrentUser()

    expect(user.full_name).toBe('الاسم المحدث')
    expect(store.currentUser.full_name).toBe('الاسم المحدث')
    expect(JSON.parse(localStorage.getItem('user')).plans_count).toBe(3)
  })
})
