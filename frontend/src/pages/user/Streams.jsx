import { useState, useEffect } from 'react'
import { dashboardAPI } from '../../utils/api'
import { PlusIcon, ArrowPathIcon, CalendarIcon, VideoCameraIcon } from '@heroicons/react/24/outline'
import { useNavigate, useLocation } from 'react-router-dom'
import axios from 'axios'

export default function Streams() {
  const [streams, setStreams] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [viewerCounts, setViewerCounts] = useState({}) // { streamId: viewerCount }
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    loadStreams()
    
    // Check if we should open create modal with pre-selected video
    if (location.state?.openCreate && location.state?.videoId) {
      setShowModal(true)
    }
    
    // Auto-refresh streams every 10 seconds (only when modal is closed)
    const interval = setInterval(() => {
      if (!showModal) {
        loadStreams(false) // silent refresh
      }
    }, 10000)
    
    return () => {
      clearInterval(interval)
    }
  }, [location, showModal])

  // Separate effect for viewer counts
  useEffect(() => {
    // Update viewer counts every 15 seconds
    const viewerInterval = setInterval(() => {
      updateViewerCounts()
    }, 15000)
    
    // Initial viewer count update
    updateViewerCounts()
    
    return () => {
      clearInterval(viewerInterval)
    }
  }, [streams])

  const loadStreams = async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true)
      }
      const response = await dashboardAPI.getStreams()
      setStreams(response.data.streams || [])
    } catch (error) {
      console.error('Failed to load streams:', error)
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }

  const updateViewerCounts = async () => {
    // Get viewer counts for live streams from Go service
    const liveStreams = streams.filter(s => s.status === 'live')
    if (liveStreams.length === 0) return

    const goServiceUrl = import.meta.env.VITE_API_URL || ''
    const counts = {}

    await Promise.all(
      liveStreams.map(async (stream) => {
        try {
          // Use check-update endpoint to get online count
          const response = await axios.post(`${goServiceUrl}/check-update`, {
            stream_id: stream.id,
            last_id: 0
          })
          if (response.data.online !== undefined) {
            counts[stream.id] = response.data.online
          }
        } catch (error) {
          console.error(`[Streams] Error getting viewer count for stream ${stream.id}:`, error)
        }
      })
    )

    if (Object.keys(counts).length > 0) {
      setViewerCounts(prev => ({ ...prev, ...counts }))
    }
  }

  const handleCreateStream = async (streamData) => {
    await dashboardAPI.createStream(streamData)
    await loadStreams()
    setShowModal(false)
  }

  const formatDate = (isoString) => {
    if (!isoString) return 'نامشخص'
    const date = new Date(isoString)
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Tehran'
    }).format(date)
  }

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

  const getStatusBadge = (status, error = null) => {
    const badges = {
      scheduled: { text: 'زمان‌بندی شده', class: 'bg-blue-100 text-blue-700' },
      live: { text: 'در حال پخش', class: 'bg-green-100 text-green-700' },
      ended: { text: 'پایان یافته', class: 'bg-gray-100 text-gray-700' },
      cancelled: { text: error ? 'خطا: ' + (error.length > 50 ? error.substring(0, 50) + '...' : error) : 'لغو شده', class: 'bg-red-100 text-red-700' }
    }
    const badge = badges[status] || { text: status, class: 'bg-gray-100 text-gray-700' }
    return <span className={`px-2 py-1 rounded text-xs ${badge.class}`} title={error || ''}>{badge.text}</span>
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    alert('لینک کپی شد!')
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold">مدیریت استریم‌ها</h1>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          <button
            onClick={loadStreams}
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
            <span className="hidden sm:inline">ایجاد استریم</span>
            <span className="sm:hidden">ایجاد</span>
          </button>
        </div>
      </div>

      <div className="card">
        {loading && streams.length === 0 ? (
          <div className="text-center py-12">در حال بارگذاری...</div>
        ) : streams.length > 0 ? (
          <div className="space-y-4">
            {streams.map((stream) => (
              <div key={stream.id} className="border rounded-lg p-3 sm:p-4 hover:bg-gray-50">
                <div className="flex flex-col sm:flex-row justify-between items-start gap-3 mb-3">
                  <div className="flex-1 w-full">
                    <h3 className="text-base sm:text-lg font-bold mb-1">{stream.title}</h3>
                    {stream.caption && (
                      <p className="text-xs sm:text-sm text-gray-600 mb-2 line-clamp-2">{stream.caption}</p>
                    )}
                    <div className="flex flex-wrap gap-2 sm:gap-4 text-xs sm:text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <CalendarIcon className="w-4 h-4" />
                        {formatDate(stream.start_time)}
                      </span>
                      <span className="flex items-center gap-1">
                        <VideoCameraIcon className="w-4 h-4" />
                        {formatDuration(stream.duration)}
                      </span>
                      {stream.status === 'live' && viewerCounts[stream.id] !== undefined && (
                        <span className="flex items-center gap-1 text-green-600">
                          👥 {viewerCounts[stream.id]} بیننده
                        </span>
                      )}
                      {stream.ended_at && (
                        <span className="text-gray-500">
                          پایان: {formatDate(new Date(new Date(stream.ended_at).getTime() + 5 * 60 * 1000).toISOString())}
                        </span>
                      )}
                      {stream.status === 'scheduled' && stream.start_time && stream.duration && (
                        <span className="text-gray-500">
                          پایان تقریبی: {formatDate(new Date(new Date(stream.start_time).getTime() + stream.duration * 1000 + 5 * 60 * 1000).toISOString())}
                        </span>
                      )}
                      {stream.status === 'live' && stream.started_at && stream.duration && (
                        <span className="text-gray-500">
                          پایان تقریبی: {formatDate(new Date(new Date(stream.started_at).getTime() + stream.duration * 1000 + 5 * 60 * 1000).toISOString())}
                        </span>
                      )}
                      {stream.channel && (
                        <span>کانال: <strong>{stream.channel.name}</strong></span>
                      )}
                      {stream.allow_comments && (
                        <span className="text-green-600">✓ کامنت فعال</span>
                      )}
                    </div>
                  </div>
                  {getStatusBadge(stream.status, stream.error_message)}
                </div>

                <div className="flex flex-col sm:flex-row gap-2 mt-3 pt-3 border-t">
                  <div className="flex gap-2 flex-1">
                    <input
                      type="text"
                      value={stream.play_link}
                      readOnly
                      className="flex-1 px-2 sm:px-3 py-1.5 sm:py-2 border rounded text-xs sm:text-sm bg-gray-50 min-w-0"
                      dir="ltr"
                    />
                    <button
                      onClick={() => copyToClipboard(stream.play_link)}
                      className="btn-secondary text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2 flex-shrink-0"
                      title="کپی لینک"
                    >
                      <span className="hidden sm:inline">📋 کپی</span>
                      <span className="sm:hidden">📋</span>
                    </button>
                    <button
                      onClick={() => window.open(stream.play_link, '_blank')}
                      className="btn-primary text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2 flex-shrink-0"
                      title="باز کردن"
                    >
                      <span className="hidden sm:inline">🔗 باز کردن</span>
                      <span className="sm:hidden">🔗</span>
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {/* Cancel button for scheduled and live streams */}
                    {(stream.status === 'scheduled' || stream.status === 'live') && (
                      <button
                        onClick={async () => {
                          if (confirm('آیا مطمئن هستید که می‌خواهید این استریم را لغو کنید؟')) {
                            try {
                              await dashboardAPI.cancelStream(stream.id)
                              await loadStreams()
                              alert('استریم با موفقیت لغو شد')
                            } catch (error) {
                              const detail = error.response?.data?.detail || 'خطا در لغو استریم'
                              alert(typeof detail === 'string' ? detail : JSON.stringify(detail))
                            }
                          }
                        }}
                        className="btn-secondary text-xs sm:text-sm bg-red-50 text-red-700 hover:bg-red-100 px-2 sm:px-3 py-1.5 sm:py-2"
                        title="لغو استریم"
                      >
                        ❌ لغو
                      </button>
                    )}
                    {/* Manage Comments - For all streams (scheduled, live, ended) */}
                    {['scheduled', 'live', 'ended'].includes(stream.status) && (
                      <button
                        onClick={() => navigate(`/dashboard/moderation?stream=${stream.id}`)}
                        className="btn-primary text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2"
                        title="مدیریت کامنت‌ها"
                      >
                        <span className="hidden sm:inline">💬 مدیریت</span>
                        <span className="sm:hidden">💬</span>
                      </button>
                    )}
                    
                    {/* Toggle Comments - For scheduled, live, ended */}
                    {['scheduled', 'live', 'ended'].includes(stream.status) && (
                      <button
                        onClick={async () => {
                          try {
                            await dashboardAPI.toggleComments(stream.id, !stream.allow_comments)
                            // Silent refresh to update UI without showing error
                            await loadStreams(false)
                          } catch (error) {
                            // Only show error if it's a real error (not success)
                            const errorDetail = error.response?.data?.detail
                            if (errorDetail && !errorDetail.includes('success')) {
                              alert(errorDetail || 'خطا در تغییر وضعیت کامنت')
                            } else {
                              // Success - just refresh silently
                              await loadStreams(false)
                            }
                          }
                        }}
                        className={`btn-secondary text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2 ${
                          stream.allow_comments 
                            ? 'bg-green-50 text-green-700' 
                            : 'bg-gray-50 text-gray-700'
                        }`}
                        title={stream.allow_comments ? 'غیرفعال کردن کامنت' : 'فعال کردن کامنت'}
                      >
                        {stream.allow_comments ? '✅' : '❌'}
                        <span className="hidden sm:inline ml-1">کامنت</span>
                      </button>
                    )}
                  </div>
                </div>

                {stream.video && (
                  <div className="mt-2 text-xs text-gray-500">
                    ویدیو: {stream.video.title}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <VideoCameraIcon className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p>هیچ استریمی وجود ندارد</p>
            <button
              onClick={() => setShowModal(true)}
              className="btn-primary mt-4"
            >
              ایجاد اولین استریم
            </button>
          </div>
        )}
      </div>

      {showModal && (
        <CreateStreamModal
          onClose={() => {
            setShowModal(false)
            // Clear location state
            if (location.state) {
              navigate(location.pathname, { replace: true, state: {} })
            }
          }}
          onSubmit={handleCreateStream}
          preSelectedVideoId={location.state?.videoId}
        />
      )}
    </div>
  )
}

function CreateStreamModal({ onClose, onSubmit, preSelectedVideoId }) {
  const [videos, setVideos] = useState([])
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const [formData, setFormData] = useState({
    video_id: preSelectedVideoId || '',
    channel_id: '',
    title: '',
    caption: '',
    start_time: '',
    allow_comments: true
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const response = await dashboardAPI.getDashboard()
      const data = response.data
      
      // Filter ready videos
      const readyVideos = (data.videos || []).filter(v => v.status === 'ready')
      setVideos(readyVideos)
      
      // Filter approved channels
      const approvedChannels = (data.channels || []).filter(c => c.status === 'approved')
      setChannels(approvedChannels)

      // If pre-selected video, auto-fill title
      if (preSelectedVideoId) {
        const video = readyVideos.find(v => v.id === preSelectedVideoId)
        if (video) {
          setFormData(prev => ({ ...prev, title: video.title }))
        }
      }
    } catch (error) {
      console.error('Failed to load data:', error)
      setError('خطا در بارگذاری اطلاعات')
    } finally {
      setLoading(false)
    }
  }

  // Helper: Convert datetime-local input to Tehran timezone ISO string
  // The input is in format: "YYYY-MM-DDTHH:mm"
  // We assume the user entered this time in Tehran timezone
  const convertToTehranISO = (localDateTimeString) => {
    // Parse the datetime-local value
    const [datePart, timePart] = localDateTimeString.split('T')
    
    // Create ISO string with Tehran timezone (+03:30)
    // Tehran is UTC+3:30 (no DST in Iran)
    return `${datePart}T${timePart}:00+03:30`
  }

  const getMinDateTime = () => {
    // Get current time in Tehran timezone
    const now = new Date()
    // Get Tehran time string (format: YYYY-MM-DD HH:mm:ss)
    const tehranStr = now.toLocaleString('sv-SE', { timeZone: 'Asia/Tehran' })
    // Parse it: "2025-11-02 19:30:00" -> "2025-11-02T19:30"
    const [datePart, timePart] = tehranStr.split(' ')
    const [hour, minute] = timePart.split(':')
    
    // Add 2 minutes
    const date = new Date(`${datePart}T${hour}:${minute}:00+03:30`)
    date.setMinutes(date.getMinutes() + 2)
    
    // Format back for datetime-local input (YYYY-MM-DDTHH:mm)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    
    return `${year}-${month}-${day}T${hours}:${minutes}`
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!formData.video_id || !formData.channel_id || !formData.title || !formData.start_time) {
      setError('لطفا همه فیلدهای الزامی را پر کنید')
      return
    }

    // Validate start time is at least 2 minutes from now (in Tehran timezone)
    // Parse input as Tehran timezone
    const startTimeISO = convertToTehranISO(formData.start_time)
    const inputDate = new Date(startTimeISO)
    
    // Get current time in Tehran timezone
    const now = new Date()
    // Create a date representing "now" in Tehran timezone
    const nowTehranStr = now.toLocaleString('sv-SE', { timeZone: 'Asia/Tehran' }).replace(' ', 'T')
    const nowTehran = new Date(nowTehranStr + '+03:30')
    const minTime = new Date(nowTehran.getTime() + 2 * 60 * 1000) // Add 2 minutes
    
    if (inputDate < minTime) {
      setError('زمان شروع باید حداقل 2 دقیقه از الان بعد باشد')
      return
    }

    try {
      setSubmitting(true)
      
      // Convert to ISO string with Tehran timezone (already done above)
      
      // Send with converted timezone
      await onSubmit({
        ...formData,
        start_time: startTimeISO
      })
      onClose()
    } catch (error) {
      const detail = error.response?.data?.detail || 'خطا در ایجاد استریم'
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setSubmitting(false)
    }
  }

  const selectedVideo = videos.find(v => v.id === parseInt(formData.video_id))

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="card max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-2xl font-bold mb-4">ایجاد استریم جدید</h2>

        {loading ? (
          <div className="text-center py-8">در حال بارگذاری...</div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Video Selection */}
            <div>
              <label className="block mb-2 font-medium">
                ویدیو <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.video_id}
                onChange={(e) => {
                  const videoId = parseInt(e.target.value)
                  const video = videos.find(v => v.id === videoId)
                  setFormData({
                    ...formData,
                    video_id: videoId,
                    title: video?.title || formData.title
                  })
                }}
                className="input"
                disabled={preSelectedVideoId} // Locked if pre-selected
                required
              >
                <option value="">انتخاب ویدیو</option>
                {videos.map(video => (
                  <option key={video.id} value={video.id}>
                    {video.title} ({Math.floor(video.duration / 60)} دقیقه)
                  </option>
                ))}
              </select>
              {preSelectedVideoId && (
                <p className="text-xs text-gray-500 mt-1">
                  ⚠️ ویدیو انتخاب شده و قابل تغییر نیست
                </p>
              )}
            </div>

            {/* Channel Selection */}
            <div>
              <label className="block mb-2 font-medium">
                کانال پخش <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.channel_id}
                onChange={(e) => setFormData({ ...formData, channel_id: parseInt(e.target.value) })}
                className="input"
                required
              >
                <option value="">انتخاب کانال</option>
                {channels.map(channel => (
                  <option key={channel.id} value={channel.id}>
                    {channel.name}
                  </option>
                ))}
              </select>
              {channels.length === 0 && (
                <p className="text-xs text-red-500 mt-1">
                  شما هیچ کانال تایید شده‌ای ندارید
                </p>
              )}
            </div>

            {/* Title */}
            <div>
              <label className="block mb-2 font-medium">
                عنوان <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="input"
                placeholder="عنوان استریم"
                required
              />
            </div>

            {/* Caption */}
            <div>
              <label className="block mb-2 font-medium">توضیحات (کپشن)</label>
              <textarea
                value={formData.caption}
                onChange={(e) => setFormData({ ...formData, caption: e.target.value })}
                className="input"
                rows="3"
                placeholder="توضیحات استریم (اختیاری)"
              />
            </div>

            {/* Start Time */}
            <div>
              <label className="block mb-2 font-medium">
                زمان شروع <span className="text-red-500">*</span>
              </label>
              <input
                type="datetime-local"
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                min={getMinDateTime()}
                className="input"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                ⏰ حداقل 2 دقیقه از الان بعد
              </p>
            </div>

            {/* Allow Comments */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="allow_comments"
                checked={formData.allow_comments}
                onChange={(e) => setFormData({ ...formData, allow_comments: e.target.checked })}
                className="w-4 h-4"
              />
              <label htmlFor="allow_comments" className="font-medium">
                اجازه کامنت
              </label>
            </div>

            {/* Selected Video Info */}
            {selectedVideo && (
              <div className="bg-blue-50 p-3 rounded text-sm">
                <p className="font-medium mb-1">📹 ویدیو انتخاب شده:</p>
                <p>{selectedVideo.title}</p>
                <p className="text-gray-600">
                  مدت زمان: {Math.floor(selectedVideo.duration / 60)} دقیقه و {selectedVideo.duration % 60} ثانیه
                </p>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded">
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="btn-secondary flex-1"
                disabled={submitting}
              >
                انصراف
              </button>
              <button
                type="submit"
                className="btn-primary flex-1"
                disabled={submitting || channels.length === 0}
              >
                {submitting ? 'در حال ایجاد...' : 'ایجاد استریم'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
