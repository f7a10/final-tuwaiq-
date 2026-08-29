import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api, apiRequest } from './api'

describe('apiRequest', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('adds the saved bearer token to protected requests', async () => {
    localStorage.setItem('auth_token', 'test-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 7 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await apiRequest('/api/me')

    expect(fetchMock).toHaveBeenCalledWith('/api/me', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
    }))
  })

  it('throws an ApiError with the Arabic backend detail', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'المشروع غير موجود' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(apiRequest('/api/projects/404')).rejects.toMatchObject({
      name: 'ApiError',
      message: 'المشروع غير موجود',
      status: 404,
    })
    expect(ApiError).toBeTypeOf('function')
  })

  it('uploads a floor plan as multipart data without forcing a content type', async () => {
    localStorage.setItem('auth_token', 'upload-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ task_id: 'task-1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const file = new File(['plan'], 'ground-floor.png', { type: 'image/png' })

    await api.projects.upload(file, { title: 'الدور الأرضي' })

    const [, request] = fetchMock.mock.calls[0]
    expect(request.method).toBe('POST')
    expect(request.body).toBeInstanceOf(FormData)
    expect(request.body.get('file')).toBe(file)
    expect(JSON.parse(request.body.get('settings'))).toMatchObject({ title: 'الدور الأرضي' })
    expect(request.headers).not.toHaveProperty('Content-Type')
    expect(request.headers.Authorization).toBe('Bearer upload-token')
  })

  it('builds encoded project filters without sending empty values', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ projects: [], total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.projects.list({ search: 'فيلا العائلة', status: 'non_compliant', empty: '' })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/projects/me?search=%D9%81%D9%8A%D9%84%D8%A7+%D8%A7%D9%84%D8%B9%D8%A7%D8%A6%D9%84%D8%A9&status_filter=non_compliant')
  })

  it('sends login credentials as JSON', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ access_token: 'new-token' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.auth.login({ email: 'fahad@example.com', password: 'secret123' })

    const [path, request] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/auth/login')
    expect(request.method).toBe('POST')
    expect(request.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(request.body)).toEqual({ email: 'fahad@example.com', password: 'secret123' })
  })

  it('loads the authenticated user from the canonical auth endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 1, full_name: 'فهد' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.auth.me()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/auth/me')
  })

  it('registers a homeowner through the canonical auth endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ user_id: 9 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const payload = {
      full_name: 'فهد',
      email: 'fahad@example.com',
      password: 'secret123',
      account_type: 'personal',
    }

    await api.auth.register(payload)

    const [path, request] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/auth/register')
    expect(JSON.parse(request.body)).toEqual(payload)
  })

  it('loads one project by its database id', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 7, title: 'الدور الأرضي' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.projects.get(7)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/projects/7')
  })

  it('loads the current approved project report', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ schema_version: 'emad.project-report.v1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.projects.report(7)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/projects/7/report')
  })

  it('loads the real admin user list', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([{ id: 1, name: 'مدير', role: 'admin' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.admin.users.list()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/auth/users')
  })

  it('requests a typed edit intent for a project', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ready', base_revision: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const payload = {
      prompt: 'حرّك الجدار 50 سم',
      selection: {
        room_id: 'room-left',
        element_id: 'wall-shared',
        element_type: 'wall',
      },
      revision: 0,
    }

    await api.editor.planIntent(7, payload)

    const [path, request] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/projects/7/edit-intent')
    expect(JSON.parse(request.body)).toEqual(payload)
  })

  it('loads the persisted editor session for a project', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ revision_number: 2, geometry: { rooms: [] } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.editor.getState(7)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/projects/7/editor')
  })

  it('creates a deterministic editor preview against a base revision', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ preview_id: 4, status: 'pending' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const payload = {
      base_revision_id: 'a'.repeat(64),
      wall_id: 'wall:room_1:room_2:v',
      offset_mm: 500,
      label_ar: 'توسيع غرفة المعيشة',
    }

    await api.editor.createPreview(7, payload)

    const [path, request] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/projects/7/editor/previews')
    expect(JSON.parse(request.body)).toEqual(payload)
  })

  it('approves an editor preview with an explicit structural review decision', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ revision_number: 1 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.editor.approvePreview(7, 4, { structural_review_confirmed: true })

    const [path, request] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/projects/7/editor/previews/4/approve')
    expect(JSON.parse(request.body)).toEqual({ structural_review_confirmed: true })
  })

  it('confirms the detected scale and geometry before metric approval', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ scale_confidence: 1, geometry_confidence: 1 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const payload = { scale_confirmed: true, geometry_confirmed: true }

    await api.editor.confirmDraft(7, payload)

    const [path, request] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/projects/7/editor/confirm')
    expect(JSON.parse(request.body)).toEqual(payload)
  })

  it('discards a persisted editor preview', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ pending_preview: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.editor.discardPreview(7, 4)

    const [path, request] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/projects/7/editor/previews/4/discard')
    expect(request.method).toBe('POST')
  })

  it.each([
    ['undo', '/api/projects/7/editor/undo'],
    ['redo', '/api/projects/7/editor/redo'],
  ])('uses the persisted %s transition', async (method, expectedPath) => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ revision_number: 1 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await api.editor[method](7)

    const [path, request] = fetchMock.mock.calls[0]
    expect(path).toBe(expectedPath)
    expect(request.method).toBe('POST')
  })
})
