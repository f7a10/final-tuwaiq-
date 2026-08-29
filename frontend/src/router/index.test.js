import { describe, expect, it } from 'vitest'

import { routes } from './index'

describe('application routes', () => {
  it('keeps the homeowner journey under project URLs', () => {
    const routeByName = Object.fromEntries(
      routes.filter((route) => route.name).map((route) => [route.name, route.path]),
    )

    expect(routeByName.projects).toBe('/projects')
    expect(routeByName.project).toBe('/projects/:id')
    expect(routeByName.editor).toBe('/projects/:id/editor')
  })

  it('redirects legacy history and dashboard URLs', () => {
    const history = routes.find((route) => route.path === '/history')
    const dashboard = routes.find((route) => route.path === '/dashboard/:id')

    expect(history.redirect).toBe('/projects')
    expect(dashboard.redirect({ params: { id: 'task-9' } })).toEqual('/projects/task-9')
  })
})
