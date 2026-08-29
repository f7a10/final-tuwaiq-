export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

export async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = localStorage.getItem('auth_token')

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(path, { ...options, headers })
  const payload = await response.json()

  if (!response.ok) {
    const message = payload.detail || payload.error || 'تعذر إكمال الطلب'
    throw new ApiError(message, response.status, payload)
  }

  return payload
}

export const api = {
  auth: {
    login(credentials) {
      return apiRequest('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      })
    },
    register(user) {
      return apiRequest('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      })
    },
    me() {
      return apiRequest('/api/auth/me')
    },
  },
  projects: {
    upload(file, settings) {
      const body = new FormData()
      body.append('file', file)
      body.append('settings', JSON.stringify(settings))
      return apiRequest('/api/upload', { method: 'POST', body })
    },
    list(filters = {}) {
      const params = new URLSearchParams()
      if (filters.search) params.set('search', filters.search)
      if (filters.status) params.set('status_filter', filters.status)
      const query = params.toString()
      return apiRequest(`/api/projects/me${query ? `?${query}` : ''}`)
    },
    get(projectId) {
      return apiRequest(`/api/projects/${projectId}`)
    },
    report(projectId) {
      return apiRequest(`/api/projects/${projectId}/report`)
    },
  },
  admin: {
    users: {
      list() {
        return apiRequest('/api/auth/users')
      },
    },
  },
  editor: {
    getState(projectId) {
      return apiRequest(`/api/projects/${projectId}/editor`)
    },
    createPreview(projectId, payload) {
      return apiRequest(`/api/projects/${projectId}/editor/previews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    },
    approvePreview(projectId, previewId, payload) {
      return apiRequest(`/api/projects/${projectId}/editor/previews/${previewId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    },
    confirmDraft(projectId, payload) {
      return apiRequest(`/api/projects/${projectId}/editor/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    },
    discardPreview(projectId, previewId) {
      return apiRequest(`/api/projects/${projectId}/editor/previews/${previewId}/discard`, { method: 'POST' })
    },
    undo(projectId) {
      return apiRequest(`/api/projects/${projectId}/editor/undo`, { method: 'POST' })
    },
    redo(projectId) {
      return apiRequest(`/api/projects/${projectId}/editor/redo`, { method: 'POST' })
    },
    planIntent(projectId, payload) {
      return apiRequest(`/api/projects/${projectId}/edit-intent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    },
  },
}
