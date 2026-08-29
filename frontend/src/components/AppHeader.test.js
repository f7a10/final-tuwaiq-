import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'

import AppHeader from './AppHeader.vue'

function mountHeader() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/projects', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
      { path: '/register', component: { template: '<div />' } },
      { path: '/profile', component: { template: '<div />' } },
      { path: '/admin', component: { template: '<div />' } },
    ],
  })

  return mount(AppHeader, {
    global: { plugins: [createPinia(), router] },
  })
}

describe('AppHeader', () => {
  it('keeps the two primary homeowner destinations visible', () => {
    const wrapper = mountHeader()

    expect(wrapper.text()).toContain('عماد')
    expect(wrapper.text()).toContain('مخطط جديد')
    expect(wrapper.text()).toContain('مشاريعي')
  })
})
