import { useState, useEffect } from 'react'
import { dashboardAPI } from '../../utils/api'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'

export default function UserChannels() {
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    loadChannels()
    
    // Auto-refresh every 10 seconds (only when modal is closed)
    const interval = setInterval(() => {
      if (!showModal) {
        loadChannels(false) // silent refresh
      }
    }, 10000)
    
    return () => clearInterval(interval)
  }, [showModal])

  const loadChannels = async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true)
      }
      const response = await dashboardAPI.getDashboard()
      const channelsList = response.data?.channels || []
      setChannels(channelsList)
    } catch (error) {
      console.error('Error loading channels:', error.message)
      if (showLoading) {
        setChannels([])
      }
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }

  const handleCreateChannel = async (name, aparatInput, rtmpUrl, rtmpKey) => {
    try {
      await dashboardAPI.createChannel(name, aparatInput, rtmpUrl, rtmpKey)
      setShowModal(false)
      loadChannels()
    } catch (error) {
      alert(error.response?.data?.detail || 'خطا در ایجاد کانال')
    }
  }

  const handleDeleteChannel = async (id) => {
    if (!confirm('آیا مطمئن هستید؟')) return
    try {
      await dashboardAPI.deleteChannel(id)
      loadChannels()
    } catch (error) {
      alert(error.response?.data?.detail || 'خطا در حذف کانال')
    }
  }

  if (loading) {
    return <div className="text-center py-12">در حال بارگذاری...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">مدیریت کانال‌ها</h1>
        <button
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <PlusIcon className="w-5 h-5" />
          کانال جدید
        </button>
      </div>

      <div className="card">
        {loading && channels.length === 0 ? (
          <div className="text-center py-12">در حال بارگذاری...</div>
        ) : channels.length > 0 ? (
          <div className="space-y-4">
            {channels.map((channel) => (
              <div key={channel.id} className="border rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg mb-2">{channel.name}</h3>
                    <div className="space-y-1 text-sm text-gray-600 mb-2">
                      {channel.aparat_username && (
                        <p>
                          📺 آپارات: <a 
                            href={channel.aparat_link || `https://www.aparat.com/${channel.aparat_username}`}
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="text-blue-600 hover:underline"
                          >
                            {channel.aparat_username}
                          </a>
                        </p>
                      )}
                      {channel.created_at && (
                        <p className="text-xs text-gray-500">
                          📅 ایجاد شده: {new Date(channel.created_at).toLocaleString('fa-IR', {
                            year: 'numeric',
                            month: 'long',
                            timeZone: 'Asia/Tehran',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </p>
                      )}
                    </div>
                    <span className={`inline-block px-2 py-1 rounded text-xs ${
                      channel.status === 'approved' ? 'bg-green-100 text-green-700' :
                      channel.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                      channel.status === 'rejected' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {channel.status === 'approved' ? '✅ تایید شده' :
                       channel.status === 'pending' ? '⏳ در انتظار تایید' :
                       channel.status === 'rejected' ? '❌ رد شده' : channel.status}
                    </span>
                  </div>
                  <button
                    onClick={() => handleDeleteChannel(channel.id)}
                    className="text-red-600 hover:text-red-800 ml-4"
                    title="حذف کانال"
                  >
                    <TrashIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">کانالی وجود ندارد</p>
            <button onClick={loadChannels} className="btn-secondary text-sm">
              بروزرسانی مجدد
            </button>
          </div>
        )}
      </div>

      {showModal && (
        <ChannelModal
          onClose={() => setShowModal(false)}
          onSubmit={handleCreateChannel}
        />
      )}
    </div>
  )
}

function ChannelModal({ onClose, onSubmit }) {
  const [name, setName] = useState('')
  const [aparatInput, setAparatInput] = useState('')
  const [rtmpUrl, setRtmpUrl] = useState('')
  const [rtmpKey, setRtmpKey] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!rtmpUrl.startsWith('rtmp://')) {
      alert('آدرس RTMP باید با rtmp:// شروع شود')
      return
    }
    onSubmit(name, aparatInput, rtmpUrl, rtmpKey)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card max-w-md w-full">
        <h2 className="text-2xl font-bold mb-4">کانال جدید</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">نام کانال</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input w-full"
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              لینک یا نام کاربری آپارات
            </label>
            <input
              type="text"
              value={aparatInput}
              onChange={(e) => setAparatInput(e.target.value)}
              className="input w-full"
              placeholder="https://www.aparat.com/metasina3 یا metasina3"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              می‌توانید لینک کامل آپارات یا فقط نام کاربری را وارد کنید
            </p>
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">آدرس RTMP</label>
            <input
              type="text"
              value={rtmpUrl}
              onChange={(e) => setRtmpUrl(e.target.value)}
              className="input w-full"
              placeholder="rtmp://..."
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">کلید RTMP</label>
            <input
              type="text"
              value={rtmpKey}
              onChange={(e) => setRtmpKey(e.target.value)}
              className="input w-full"
              required
            />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              انصراف
            </button>
            <button type="submit" className="btn-primary flex-1">
              ایجاد
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

