import { useState, useEffect } from 'react'
import { PlusIcon, TrashIcon, ArrowPathIcon, PencilIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline'
import api, { dashboardAPI } from '../../utils/api'

export default function UserVideos() {
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [playingVideo, setPlayingVideo] = useState(null)

  useEffect(() => {
    loadVideos()
    
    // Auto-refresh every 10 seconds (only when modal is closed)
    const interval = setInterval(() => {
      if (!showModal) {
        loadVideos(false) // silent refresh
      }
    }, 10000)
    
    return () => clearInterval(interval)
  }, [showModal])

  const loadVideos = async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true)
      }
      const response = await dashboardAPI.getDashboard()
      
      if (!response || !response.data) {
        throw new Error('Invalid response from server')
      }
      
      const videosList = Array.isArray(response.data?.videos) ? response.data.videos : []
      setVideos(videosList)
      
    } catch (error) {
      console.error('Error loading videos:', error.message)
      if (showLoading) {
        setVideos([])
        const errorMsg = error.response?.data?.detail || error.message || 'خطا در ارتباط با سرور'
        alert('خطا در بارگذاری ویدیوها: ' + errorMsg)
      }
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }

  const handleUploadVideo = async (title, file, setProgress, abortController) => {
    try {
      const CHUNK_SIZE = 1 * 1024 * 1024 // 1MB for smoother progress

      // Small files: single request with progress
      if (file.size <= CHUNK_SIZE) {
        const formData = new FormData()
        formData.append('title', title)
        formData.append('file', file)
        await api.post('/api/dashboard/videos', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          signal: abortController.signal,
          timeout: 300000, // 5 minutes timeout for mobile uploads
          onUploadProgress: (e) => {
            if (e.total) {
              const pct = Math.floor((e.loaded / e.total) * 100)
              setProgress(pct)
            }
          },
        })
        setProgress(100)
        await new Promise(resolve => setTimeout(resolve, 500))
        await loadVideos()
        setShowModal(false)
        return
      }

      // Large files: Resumable, chunked upload
      const uploadId = `${file.name}-${file.size}`.replace(/[^a-zA-Z0-9_.-]/g, '')
      // Resume check
      let received = 0
      try {
        const st = await api.get('/api/dashboard/videos/upload-status', { params: { upload_id: uploadId } })
        if (st.data?.exists) received = st.data.received || 0
      } catch (_) {}
      let offset = received - (received % CHUNK_SIZE)
      while (offset < file.size) {
        // Check if cancelled
        if (abortController.signal.aborted) {
          throw new Error('آپلود توسط کاربر لغو شد')
        }
        
        const end = Math.min(offset + CHUNK_SIZE, file.size)
        const blob = file.slice(offset, end)
        const contentRange = `bytes ${offset}-${end - 1}/${file.size}`
        // optimistic progress before request finishes
        const optimistic = Math.min(99, Math.floor(((end) / file.size) * 100))
        setProgress(optimistic)
        const res = await api.post('/api/dashboard/videos/upload-chunk', blob, {
          headers: {
            'Content-Type': 'application/octet-stream',
            'Upload-Id': uploadId,
            'Content-Range': contentRange,
            'X-File-Size': file.size,
          },
          params: { filename: file.name, title: title },
          signal: abortController.signal,
          timeout: 300000, // 5 minutes timeout for mobile uploads
        })
        if (res.data?.received != null) {
          received = res.data.received
          setProgress(Math.floor((received / file.size) * 100))
          offset = received
        }
        if (res.data?.completed) {
          setProgress(100)
          await new Promise(resolve => setTimeout(resolve, 500))
          await loadVideos()
          setShowModal(false)
          return
        }
        offset = end
      }
      setProgress(100)
      await new Promise(resolve => setTimeout(resolve, 500))
      await loadVideos()
      setShowModal(false)
    } catch (error) {
      // Handle cancel error
      if (error.name === 'CanceledError' || error.message === 'آپلود توسط کاربر لغو شد') {
        throw error
      }
      
      let msg = 'خطا در آپلود ویدیو'
      const res = error.response
      if (res) {
        if (typeof res.data === 'string') {
          msg = res.data
        } else if (res.data?.detail) {
          const d = res.data.detail
          if (Array.isArray(d)) {
            msg = d.map((e) => e.msg || e.detail || JSON.stringify(e)).join(' | ')
          } else if (typeof d === 'object') {
            msg = d.msg || d.detail || JSON.stringify(d)
          } else {
            msg = String(d)
          }
        } else if (res.status) {
          msg = `HTTP ${res.status}`
        }
      } else if (error.message) {
        msg = error.message
      }
      console.error('Upload error:', error)
      alert(msg)
      throw error
    }
  }

  const handleDeleteVideo = async (id) => {
    if (!confirm('آیا مطمئن هستید؟')) return
    try {
      await dashboardAPI.deleteVideo(id)
      loadVideos()
    } catch (error) {
      alert(error.response?.data?.detail || 'خطا در حذف ویدیو')
    }
  }

  const handleUpdateVideoTitle = async (id, newTitle) => {
    if (!newTitle || newTitle.trim() === '') {
      alert('عنوان نمی‌تواند خالی باشد')
      return false
    }
    try {
      await dashboardAPI.updateVideoTitle(id, newTitle.trim())
      // Update local state immediately
      setVideos(prev => prev.map(v => v.id === id ? { ...v, title: newTitle.trim() } : v))
      return true
    } catch (error) {
      alert(error.response?.data?.detail || 'خطا در تغییر عنوان')
      return false
    }
  }

  if (loading) {
    return <div className="text-center py-12">در حال بارگذاری...</div>
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold">مدیریت ویدیوها</h1>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          <button
            onClick={loadVideos}
            className="btn-secondary flex items-center gap-2 text-sm px-3 py-2 flex-1 sm:flex-initial"
            disabled={loading}
          >
            <ArrowPathIcon className={`w-4 h-4 sm:w-5 sm:h-5 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">بروزرسانی</span>
            <span className="sm:hidden">بروز</span>
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="btn-primary flex items-center gap-2 text-sm px-3 py-2 flex-1 sm:flex-initial"
          >
            <PlusIcon className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="hidden sm:inline">آپلود ویدیو</span>
            <span className="sm:hidden">آپلود</span>
          </button>
        </div>
      </div>

      <div className="card">
        {loading && videos.length === 0 ? (
          <div className="text-center py-12">در حال بارگذاری...</div>
        ) : videos.length > 0 ? (
          <div className="space-y-4">
            {videos.map((video) => {
              const formatDuration = (seconds) => {
                if (!seconds || seconds === 0) return 'نامشخص'
                const hours = Math.floor(seconds / 3600)
                const mins = Math.floor((seconds % 3600) / 60)
                const secs = seconds % 60
                if (hours > 0) {
                  return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
                }
                return `${mins}:${secs.toString().padStart(2, '0')}`
              }
              
              return (
                <VideoItem
                  key={video.id}
                  video={video}
                  onUpdateTitle={handleUpdateVideoTitle}
                  onDelete={handleDeleteVideo}
                  onPlay={() => setPlayingVideo(video)}
                  formatDuration={formatDuration}
                />
              )
            })}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">ویدیویی وجود ندارد</p>
            <button onClick={loadVideos} className="btn-secondary text-sm">
              <ArrowPathIcon className="w-4 h-4 inline mr-1" />
              بروزرسانی مجدد
            </button>
          </div>
        )}
      </div>

      {showModal && (
        <VideoUploadModal
          onClose={() => setShowModal(false)}
          onSubmit={handleUploadVideo}
        />
      )}

      {playingVideo && (
        <VideoPlayerModal
          video={playingVideo}
          onClose={() => setPlayingVideo(null)}
        />
      )}
    </div>
  )
}

function VideoItem({ video, onUpdateTitle, onDelete, onPlay, formatDuration }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(video.title || '')

  // Update editTitle when video.title changes (e.g., after refresh)
  useEffect(() => {
    if (!isEditing) {
      setEditTitle(video.title || '')
    }
  }, [video.title, isEditing])

  const handleSave = async () => {
    const success = await onUpdateTitle(video.id, editTitle)
    if (success) {
      setIsEditing(false)
    }
  }

  const handleCancel = () => {
    setEditTitle(video.title || '')
    setIsEditing(false)
  }

  return (
    <div className="border rounded-lg p-3 sm:p-4">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3">
        <div className="flex-1 w-full">
          {isEditing ? (
            <div className="flex items-center gap-2 mb-2">
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="input flex-1 text-base sm:text-lg font-semibold"
                autoFocus
                maxLength={255}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSave()
                  } else if (e.key === 'Escape') {
                    handleCancel()
                  }
                }}
              />
              <button
                onClick={handleSave}
                className="text-green-600 hover:text-green-800 p-1"
                title="ذخیره"
              >
                <CheckIcon className="w-5 h-5" />
              </button>
              <button
                onClick={handleCancel}
                className="text-red-600 hover:text-red-800 p-1"
                title="لغو"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 mb-2">
              <h3 className="font-semibold text-base sm:text-lg flex-1">{video.title || 'بدون عنوان'}</h3>
              <button
                onClick={() => setIsEditing(true)}
                className="text-gray-500 hover:text-gray-700 p-1"
                title="ویرایش عنوان"
              >
                <PencilIcon className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-gray-600 mb-2">
            <span className="flex items-center gap-1">
              <span>⏱️</span>
              <span>مدت زمان: <strong>{formatDuration(video.duration)}</strong></span>
            </span>
            {video.created_at && (
              <span className="flex items-center gap-1">
                <span>📅</span>
                <span>آپلود: <strong>{new Date(video.created_at).toLocaleString('fa-IR', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                  timeZone: 'Asia/Tehran'
                })}</strong></span>
              </span>
            )}
            {video.file_size > 0 && (
              <span className="flex items-center gap-1">
                <span>💾</span>
                <span>حجم: <strong>{Math.round(video.file_size / 1024 / 1024)} MB</strong></span>
              </span>
            )}
          </div>
          <span className={`inline-block px-2 py-1 rounded text-xs ${
            video.status === 'ready' ? 'bg-green-100 text-green-700' :
            video.status === 'awaiting_approval' ? 'bg-yellow-100 text-yellow-700' :
            video.status === 'processing' ? 'bg-blue-100 text-blue-700' :
            video.status === 'pending' ? 'bg-gray-100 text-gray-700' :
            video.status === 'rejected' ? 'bg-red-100 text-red-700' :
            'bg-gray-100 text-gray-700'
          }`}>
            {video.status === 'ready' ? 'آماده' :
             video.status === 'awaiting_approval' ? 'در انتظار تایید' :
             video.status === 'processing' ? 'در حال پردازش' :
             video.status === 'pending' ? 'در انتظار' :
             video.status === 'rejected' ? 'رد شده' : video.status}
          </span>
        </div>
        <div className="flex flex-wrap gap-2 items-center mt-2 sm:mt-0">
          {(video.processed_file || video.original_file) && (
            <button
              onClick={onPlay}
              className="btn-secondary text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2"
              title="پخش ویدیو"
            >
              <span className="hidden sm:inline">▶️ پخش</span>
              <span className="sm:hidden">▶️</span>
            </button>
          )}
          {video.status === 'ready' && (
            <button
              onClick={() => {
                window.location.href = '/dashboard/streams?videoId=' + video.id
              }}
              className="btn-primary text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2"
              title="استفاده برای استریم"
            >
              <span className="hidden sm:inline">📡 استریم</span>
              <span className="sm:hidden">📡</span>
            </button>
          )}
          <button
            onClick={() => onDelete(video.id)}
            className="text-red-600 hover:text-red-800 p-1.5 sm:p-2"
            title="حذف ویدیو"
          >
            <TrashIcon className="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}

function VideoPlayerModal({ video, onClose }) {
  const API_URL = import.meta.env.VITE_API_URL || ''
  const videoUrl = `${API_URL}/api/dashboard/videos/${video.id}/play`

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg max-w-4xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b flex justify-between items-center">
          <h2 className="text-xl font-bold">{video.title}</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
          >
            ×
          </button>
        </div>
        <div className="p-4">
          <video
            controls
            autoPlay
            className="w-full rounded"
            style={{ maxHeight: '70vh' }}
          >
            <source src={videoUrl} type="video/mp4" />
            مرورگر شما از پخش ویدیو پشتیبانی نمی‌کند.
          </video>
        </div>
        <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
          <div className="text-sm text-gray-600">
            <span className={`px-2 py-1 rounded text-xs ${
              video.status === 'ready' ? 'bg-green-100 text-green-700' :
              video.status === 'awaiting_approval' ? 'bg-yellow-100 text-yellow-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {video.status === 'ready' ? 'آماده' :
               video.status === 'awaiting_approval' ? 'در انتظار تایید' :
               video.status}
            </span>
          </div>
          <button onClick={onClose} className="btn-secondary">
            بستن
          </button>
        </div>
      </div>
    </div>
  )
}

function VideoUploadModal({ onClose, onSubmit }) {
  const [title, setTitle] = useState('')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [abortController, setAbortController] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      alert('لطفا فایل ویدیو را انتخاب کنید')
      return
    }
    setError('')
    setUploading(true)
    setProgress(1)
    
    // Create abort controller for cancelling upload
    const controller = new AbortController()
    setAbortController(controller)
    
    try {
      await onSubmit(title, file, setProgress, controller)
      onClose() // Close modal on success
    } catch (e) {
      const d = e?.response?.data
      let msg = e.message || 'خطا در آپلود ویدیو'
      if (d?.detail) {
        if (Array.isArray(d.detail)) {
          msg = d.detail.map((e) => e.msg || e.detail || JSON.stringify(e)).join(' | ')
        } else if (typeof d.detail === 'object') {
          msg = d.detail.msg || d.detail.detail || JSON.stringify(d.detail)
        } else {
          msg = d.detail
        }
      }
      setError(msg)
    } finally {
      setUploading(false)
      setAbortController(null)
    }
  }

  const handleCancel = () => {
    if (uploading && abortController) {
      // Cancel ongoing upload
      abortController.abort()
      setUploading(false)
      setProgress(0)
      setError('آپلود لغو شد')
    } else {
      // Just close modal
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card max-w-md w-full">
        <h2 className="text-2xl font-bold mb-4">آپلود ویدیو</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">عنوان</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input w-full"
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">فایل ویدیو</label>
            <input
              type="file"
              accept="video/*"
              onChange={(e) => setFile(e.target.files[0])}
              className="input w-full"
              required
            />
          </div>
          {(uploading || progress > 0) && (
            <div className="mb-4 w-full bg-gray-200 rounded">
              <div className="h-2 bg-primary-600 rounded" style={{ width: `${progress}%` }}></div>
              <div className="text-xs text-gray-500 mt-1">{progress}%</div>
            </div>
          )}
          {error && <div className="text-red-600 text-sm mb-2">{error}</div>}
          <div className="flex gap-2">
            <button 
              type="button" 
              onClick={handleCancel} 
              className={uploading ? "btn-secondary flex-1 bg-red-500 hover:bg-red-600 text-white" : "btn-secondary flex-1"}
            >
              {uploading ? 'لغو آپلود' : 'انصراف'}
            </button>
            <button type="submit" className="btn-primary flex-1" disabled={uploading}>
              {uploading ? `در حال آپلود... ${progress}%` : 'آپلود'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

