import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { moderationAPI } from '../../utils/api'
import { useAuth } from '../../hooks/useAuth'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'

export default function AdminModeration() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const streamId = searchParams.get('stream') || searchParams.get('streamId')
  const [comments, setComments] = useState([])
  const [loading, setLoading] = useState(true)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const autoRemoveTimersRef = useRef({})

  useEffect(() => {
    if (streamId) {
      setLoading(true)
      // Load comments immediately via HTTP
      loadComments()
      // Also try WebSocket for real-time updates
      connectWebSocket()
      
      // Fallback: Poll every 5 seconds if WebSocket fails
      const pollInterval = setInterval(() => {
        loadComments()
      }, 5000)
      
      return () => {
        clearInterval(pollInterval)
        if (wsRef.current) {
          wsRef.current.close()
        }
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        // Clear all auto-remove timers
        Object.values(autoRemoveTimersRef.current).forEach(timer => clearTimeout(timer))
      }
    } else {
      // No streamId provided, stop loading
      setLoading(false)
    }
  }, [streamId])

  // Auto-remove comments after 15 seconds
  const scheduleAutoRemove = (commentId, createdAt) => {
    // Don't auto-remove in moderation page - let moderators see all comments
    // Auto-remove is only for the player page
    // Just schedule a timer to show warning, but don't remove
    const now = Date.now()
    const commentTime = new Date(createdAt).getTime()
    const elapsed = now - commentTime
    const remaining = 15000 - elapsed // 15 seconds

    // Only remove if already expired (more than 15 seconds old)
    if (remaining <= 0) {
      // Already expired, but keep it for moderation - just log
      console.log(`[Moderation] Comment ${commentId} is ${Math.abs(remaining/1000)}s old but keeping for moderation`)
    }
    // Don't set timer to auto-remove - moderators need to see all comments
  }

  const connectWebSocket = () => {
    if (!streamId) return

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || window.location.host
    const wsUrl = `${wsProtocol}//${wsHost}/ws/stream/${streamId}/comments`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WS] Connected to comment moderation for stream:', streamId)
        // Don't set loading to false here - wait for initial data
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('[WS] Received message:', data)

          // Handle initial comments - check for both formats
          if (data.type === 'initial' || (data.pending !== undefined || data.approved !== undefined)) {
            // Initial comments loaded - show only recent ones
            // Handle multiple formats:
            // 1. data.comments.pending/approved (nested)
            // 2. data.pending/approved (direct)
            // 3. Direct object with pending/approved at root
            console.log('[WS] Full data received:', data)
            console.log('[WS] Data structure:', {
              hasType: !!data.type,
              hasComments: !!data.comments,
              hasPending: !!data.pending,
              hasApproved: !!data.approved,
              commentsType: typeof data.comments
            })
            
            let pending = []
            let approved = []
            
            // Try nested format first: data.comments.pending/approved
            if (data.comments && typeof data.comments === 'object') {
              pending = Array.isArray(data.comments.pending) ? data.comments.pending : []
              approved = Array.isArray(data.comments.approved) ? data.comments.approved : []
              console.log('[WS] Found nested format - Pending:', pending.length, 'Approved:', approved.length)
            }
            
            // If still empty, try direct format: data.pending/approved (when type is not present or direct format)
            if (pending.length === 0 && approved.length === 0) {
              pending = Array.isArray(data.pending) ? data.pending : []
              approved = Array.isArray(data.approved) ? data.approved : []
              console.log('[WS] Found direct format - Pending:', pending.length, 'Approved:', approved.length)
            }
            
            const allComments = [...pending, ...approved]
            
            console.log('[WS] After parsing - Pending:', pending.length, 'Approved:', approved.length, 'Total:', allComments.length)
            console.log('[WS] Pending array:', pending)
            console.log('[WS] Approved array:', approved)
            
            const recent = allComments.slice(0, 100).map(c => ({
              ...c,
              created_at: c.created_at || new Date().toISOString()
            }))
            
            console.log('[WS] Setting comments:', recent.length)
            console.log('[WS] Comments array:', recent)
            
            // Always set comments, even if empty
            setComments(recent)
            setLoading(false)
            
            // Schedule auto-remove for each (but don't actually remove)
            recent.forEach(c => scheduleAutoRemove(c.id, c.created_at))
          } else if (data.type === 'new_comment') {
            // New comment received
            const comment = {
              ...data.comment,
              created_at: data.comment.created_at || new Date().toISOString()
            }
            setComments(prev => {
              const updated = [comment, ...prev].slice(0, 100)
              scheduleAutoRemove(comment.id, comment.created_at)
              return updated
            })
          } else if (data.type === 'comment_deleted') {
            // Comment deleted
            setComments(prev => prev.filter(c => c.id !== data.comment_id))
            if (autoRemoveTimersRef.current[data.comment_id]) {
              clearTimeout(autoRemoveTimersRef.current[data.comment_id])
              delete autoRemoveTimersRef.current[data.comment_id]
            }
          }
        } catch (error) {
          console.error('[WS] Error parsing message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[WS] Error:', error)
      }

      ws.onclose = () => {
        console.log('[WS] Disconnected, reconnecting...')
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket()
        }, 3000)
      }
    } catch (error) {
      console.error('[WS] Connection error:', error)
      // Fallback to HTTP polling if WebSocket fails
      loadComments()
      const pollInterval = setInterval(() => {
        loadComments()
      }, 5000)
      // Clean up interval on unmount
      return () => clearInterval(pollInterval)
    }
  }

  const loadComments = async () => {
    if (!streamId) {
      setLoading(false)
      return
    }
    
    try {
      console.log('[Moderation] Loading comments for stream:', streamId)
      const response = await moderationAPI.getComments(streamId)
      console.log('[Moderation] Comments response:', response.data)
      console.log('[Moderation] Full response:', JSON.stringify(response.data, null, 2))
      
      if (!response.data) {
        console.error('[Moderation] No data in response')
        setLoading(false)
        return
      }
      
      const pending = response.data.pending || []
      const approved = response.data.approved || []
      const allComments = [...pending, ...approved]
      
      console.log('[Moderation] Pending:', pending.length, 'Approved:', approved.length, 'Total:', allComments.length)
      console.log('[Moderation] Pending array:', pending)
      console.log('[Moderation] Approved array:', approved)
      console.log('[Moderation] All comments array:', allComments)
      
      const recent = allComments.slice(0, 100).map(c => ({
        ...c,
        created_at: c.created_at || new Date().toISOString()
      }))
      
      console.log('[Moderation] Processed comments:', recent.length)
      console.log('[Moderation] Processed comments array:', recent)
      
      // Always set comments, even if empty
      setComments(recent)
      // Schedule auto-remove for each
      recent.forEach(c => scheduleAutoRemove(c.id, c.created_at))
      setLoading(false)
    } catch (error) {
      console.error('[Moderation] Error loading comments:', error)
      console.error('[Moderation] Error details:', error.response?.data)
      console.error('[Moderation] Error status:', error.response?.status)
      console.error('[Moderation] Full error:', error)
      
      // Show error message to user
      if (error.response?.status === 401) {
        alert('لطفاً ابتدا وارد شوید')
      } else if (error.response?.status === 403) {
        alert('شما دسترسی به این صفحه ندارید')
      } else if (error.response?.status === 404) {
        alert('استریم پیدا نشد')
      } else {
        alert(`خطا در بارگذاری کامنت‌ها: ${error.response?.data?.detail || error.message}`)
      }
      
      setLoading(false)
    }
  }

  const handleDelete = async (commentId) => {
    try {
      await moderationAPI.deleteComment(streamId, commentId)
      setComments(prev => prev.filter(c => c.id !== commentId))
      if (autoRemoveTimersRef.current[commentId]) {
        clearTimeout(autoRemoveTimersRef.current[commentId])
        delete autoRemoveTimersRef.current[commentId]
      }
    } catch (error) {
      alert(error.response?.data?.detail || 'خطا در حذف نظر')
    }
  }

  const handleBack = () => {
    // Navigate back to streams page based on user role
    if (user?.role === 'admin') {
      navigate('/admin')
    } else {
      navigate('/dashboard/streams')
    }
  }

  if (!streamId) {
    return (
      <div className="text-center py-12">
        <div className="flex items-center justify-center gap-4 mb-4">
          <button
            onClick={handleBack}
            className="btn-secondary flex items-center gap-2 px-4 py-2 text-sm"
            title="بازگشت به صفحه استریم‌ها"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            <span>بازگشت</span>
          </button>
          <h1 className="text-2xl font-bold text-text-primary md:ml-20">مدیریت نظرات</h1>
        </div>
        <p className="text-text-secondary">لطفا stream ID را وارد کنید</p>
      </div>
    )
  }

  if (loading) {
    return <div className="text-center py-12">در حال بارگذاری...</div>
  }

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6">
      <div className="mb-4 sm:mb-6">
        <div className="flex items-center gap-4 mb-4">
          <button
            onClick={handleBack}
            className="btn-secondary flex items-center gap-2 px-4 py-2 text-sm"
            title="بازگشت به صفحه استریم‌ها"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            <span>بازگشت</span>
          </button>
          <h1 className="text-2xl sm:text-3xl font-bold text-text-primary">مدیریت نظرات</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-text-secondary md:ml-20">
          <span>استریم ID: {streamId}</span>
          <span className="hidden sm:inline">•</span>
          <span>تعداد کامنت‌ها: {comments.length}</span>
          <span className="hidden sm:inline">•</span>
          <span className="text-yellow-600 dark:text-yellow-400 text-xs sm:text-sm">⚠️ هر کامنت بعد از 15 ثانیه خودکار حذف می‌شود</span>
        </div>
      </div>
      
      {/* Simple Line-by-Line Comments List */}
      <div className="bg-bg-surface rounded-lg border border-border shadow-glass">
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
            <p className="mt-4 text-text-secondary">در حال بارگذاری کامنت‌ها...</p>
          </div>
        ) : comments.length === 0 ? (
          <div className="text-center py-12 text-text-secondary">
            <p>هیچ نظری وجود ندارد</p>
            <p className="text-xs mt-2">کامنت‌ها بعد از 15 ثانیه خودکار حذف می‌شوند</p>
            <button 
              onClick={() => loadComments()} 
              className="btn-primary mt-4 px-4 py-2 text-sm"
            >
              🔄 دوباره بارگذاری
            </button>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {comments.map((comment, index) => {
              return (
                <div 
                  key={comment.id} 
                  className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4 p-2 sm:p-3 hover:bg-bg transition-colors border-b border-border last:border-b-0"
                >
                  {/* Row Number */}
                  <div className="flex-shrink-0 w-8 sm:w-12 text-center">
                    <span className="text-xs sm:text-sm font-mono text-text-secondary">{index + 1}</span>
                  </div>
                  
                  {/* Username */}
                  <div className="flex-shrink-0 w-full sm:w-32">
                    <span className="text-xs sm:text-sm font-medium text-text-primary truncate block">
                      {comment.username}
                    </span>
                  </div>
                  
                  {/* Phone */}
                  <div className="flex-shrink-0 w-full sm:w-32">
                    <span className="text-xs text-text-secondary font-mono">{comment.phone}</span>
                  </div>
                  
                  {/* Message */}
                  <div className="flex-1 min-w-0 w-full sm:w-auto">
                    <p className="text-xs sm:text-sm text-text-primary break-words sm:truncate">{comment.message}</p>
                  </div>
                  
                  {/* Delete Button - Always visible, right after message */}
                  <div className="flex-shrink-0 w-full sm:w-auto">
                    <button
                      onClick={() => handleDelete(comment.id)}
                      className="w-full sm:w-auto px-2 sm:px-3 py-1 bg-red-500/20 dark:bg-red-500/30 text-red-600 dark:text-red-400 text-xs font-medium rounded hover:bg-red-500/30 dark:hover:bg-red-500/40 border border-red-500/30 dark:border-red-500/40 transition-colors"
                      title="حذف فوری"
                    >
                      حذف
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
      
      {comments.length >= 100 && (
        <p className="text-center text-sm text-orange-600 dark:text-orange-400 mt-4">
          ⚠️ حداکثر 100 کامنت نمایش داده می‌شود
        </p>
      )}
    </div>
  )
}
