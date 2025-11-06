import axios from 'axios'

// Always use api subdomain for API calls (from env)
const API_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Important for cookies
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
})

// Request interceptor
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only log errors, not normal responses
    if (error.response?.status >= 500) {
      console.error('Server error:', error.response.status)
    }
    return Promise.reject(error)
  }
)

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Only redirect to login if NOT on player page (viewer pages don't need auth)
      const isPlayerPage = window.location.pathname.startsWith('/c/')
      const isLoginPage = window.location.pathname === '/login'
      
      if (!isPlayerPage && !isLoginPage) {
        window.location.replace('/login')
      }
    }
    return Promise.reject(error)
  }
)

export default api

export const authAPI = {
  login: (identity, password) => api.post('/api/auth/login', null, { params: { identity, password } }),
  me: () => api.get('/api/auth/me'),
  logout: () => api.post('/api/auth/logout'),
}

export const adminAPI = {
  getUsers: (page = 1, perPage = 20) => api.get('/api/admin/users', { params: { page, per_page: perPage } }),
  createUser: (data) => api.post('/api/admin/users', data),
  updateUser: (id, data) => api.put(`/api/admin/users/${id}`, data),
  deleteUser: (id) => api.delete(`/api/admin/users/${id}`),
  impersonateUser: (id) => api.post(`/api/admin/users/${id}/impersonate`),
  revertImpersonation: () => api.post('/api/admin/impersonate/revert'),
  getStats: () => api.get('/api/admin/stats'),
}

export const dashboardAPI = {
  getDashboard: () => api.get('/api/dashboard/'),
  createChannel: (name, aparatInput, rtmpUrl, rtmpKey) => api.post('/api/dashboard/channels', null, { 
    params: { name, aparat_input: aparatInput, rtmp_url: rtmpUrl, rtmp_key: rtmpKey } 
  }),
  deleteChannel: (id) => api.delete(`/api/dashboard/channels/${id}`),
  uploadVideo: (formData) => api.post('/api/dashboard/videos', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  updateVideoTitle: (id, title) => {
    const formData = new FormData()
    formData.append('title', title)
    return api.put(`/api/dashboard/videos/${id}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  deleteVideo: (id) => api.delete(`/api/dashboard/videos/${id}`),
  createStream: (data) => api.post('/api/dashboard/streams', data),
  getStreams: () => api.get('/api/dashboard/streams'),
  cancelStream: (streamId) => api.post(`/api/dashboard/streams/${streamId}/cancel`),
  getShareLink: (id) => api.get(`/api/dashboard/streams/${id}/share-link`),
  toggleComments: (streamId, enabled) => api.post(`/api/dashboard/streams/${streamId}/toggle-comments`, null, { params: { enabled } }),
}

export const playerAPI = {
  getPlayer: (aparatUsername) => api.get(`/api/c/${aparatUsername}`),
  enterStream: (aparatUsername, name, phone) => api.post(`/api/c/${aparatUsername}/enter`, null, { params: { name, phone } }),
  submitComment: (aparatUsername, message) => api.post(`/api/c/${aparatUsername}/comments`, null, { params: { message } }),
  getComments: (aparatUsername, lastId = 0) => api.get(`/api/c/${aparatUsername}/comments`, { params: { last_id: lastId } }),
  getStats: (streamId) => api.get(`/api/stats/${streamId}`),
}

export const moderationAPI = {
  getComments: (streamId) => api.get(`/api/moderation/${streamId}/comments`),
  approveComment: (streamId, commentId) => api.post(`/api/moderation/${streamId}/comments/${commentId}/approve`),
  deleteComment: (streamId, commentId) => api.delete(`/api/moderation/${streamId}/comments/${commentId}`),
}

export const approvalsAPI = {
  getPending: (type = null, status = 'pending', page = 1, perPage = 20) => api.get('/api/admin/approvals', { params: { type, status, page, per_page: perPage } }),
  approve: (id) => api.post(`/api/admin/approvals/${id}/approve`),
  reject: (id, reason = null) => api.post(`/api/admin/approvals/${id}/reject`, null, { params: { reason } }),
  getVideoUrl: (id) => `${API_URL}/api/admin/approvals/${id}/video`,
}

