import { useState, useEffect } from 'react'
import { dashboardAPI } from '../../utils/api'
import { Link } from 'react-router-dom'
import { VideoCameraIcon, FilmIcon, CalendarIcon, UserGroupIcon } from '@heroicons/react/24/outline'
import axios from 'axios'

export default function UserDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [viewerStats, setViewerStats] = useState({ total: 0, average: 0 })

  useEffect(() => {
    loadDashboard()
    
    // Auto-refresh every 10 seconds (silent)
    const interval = setInterval(() => {
      loadDashboard(false) // silent refresh
    }, 10000)
    
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (data?.streams) {
      calculateViewerStats()
      
      // Auto-refresh viewer stats every 15 seconds
      const viewerInterval = setInterval(() => {
        calculateViewerStats()
      }, 15000)
      
      return () => clearInterval(viewerInterval)
    }
  }, [data?.streams])

  const loadDashboard = async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true)
      }
      const response = await dashboardAPI.getDashboard()
      setData(response.data)
    } catch (error) {
      console.error('Error loading dashboard:', error)
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }

  const calculateViewerStats = async () => {
    if (!data?.streams || data.streams.length === 0) {
      setViewerStats({ total: 0, average: 0 })
      return
    }

    const liveStreams = data.streams.filter(s => s.status === 'live')
    if (liveStreams.length === 0) {
      setViewerStats({ total: 0, average: 0 })
      return
    }

    const goServiceUrl = import.meta.env.VITE_API_URL || ''
    let totalViewers = 0

    await Promise.all(
      liveStreams.map(async (stream) => {
        try {
          const response = await axios.post(`${goServiceUrl}/check-update`, {
            stream_id: stream.id,
            last_id: 0
          })
          if (response.data.online !== undefined) {
            totalViewers += response.data.online
          }
        } catch (error) {
          // Silent error - don't log for every stream
        }
      })
    )

    const average = data.streams.length > 0 ? Math.round(totalViewers / data.streams.length) : 0
    setViewerStats({ total: totalViewers, average })
  }

  if (loading) {
    return <div className="text-center py-12">در حال بارگذاری...</div>
  }

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-bold mb-6 sm:mb-8 text-text-primary md:ml-20">داشبورد کاربری</h1>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
        <Link to="/dashboard/channels" className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-secondary text-xs sm:text-sm mb-2">کانال‌ها</p>
              <p className="text-2xl sm:text-3xl font-bold text-text-primary">{data?.channels?.length || 0}</p>
            </div>
            <div className="bg-blue-500 p-3 sm:p-4 rounded-full text-white">
              <VideoCameraIcon className="w-6 h-6 sm:w-8 sm:h-8" />
            </div>
          </div>
        </Link>
        
        <Link to="/dashboard/videos" className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-secondary text-xs sm:text-sm mb-2">ویدیوها</p>
              <p className="text-2xl sm:text-3xl font-bold text-text-primary">{data?.videos?.length || 0}</p>
            </div>
            <div className="bg-purple-500 p-3 sm:p-4 rounded-full text-white">
              <FilmIcon className="w-6 h-6 sm:w-8 sm:h-8" />
            </div>
          </div>
        </Link>
        
        <Link to="/dashboard/streams" className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-secondary text-xs sm:text-sm mb-2">استریم‌ها</p>
              <p className="text-2xl sm:text-3xl font-bold text-text-primary">{data?.streams?.length || 0}</p>
            </div>
            <div className="bg-green-500 p-3 sm:p-4 rounded-full text-white">
              <CalendarIcon className="w-6 h-6 sm:w-8 sm:h-8" />
            </div>
          </div>
        </Link>
        
        {/* Viewer Statistics Card */}
        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-secondary text-xs sm:text-sm mb-2">کل بینندگان</p>
              <p className="text-2xl sm:text-3xl font-bold text-text-primary">{viewerStats.total}</p>
              <p className="text-xs sm:text-sm text-text-secondary mt-1">
                میانگین: {viewerStats.average}
              </p>
            </div>
            <div className="bg-gradient-primary p-3 sm:p-4 rounded-full text-white">
              <UserGroupIcon className="w-6 h-6 sm:w-8 sm:h-8" />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4 text-text-primary">استریم‌های اخیر</h2>
        {data?.streams?.length > 0 ? (
          <div className="space-y-2">
            {data.streams.slice(0, 5).map((stream) => (
              <div key={stream.id} className="border border-border rounded-lg p-3 sm:p-4 hover:border-glow transition-colors">
                <p className="font-medium text-sm sm:text-base text-text-primary">{stream.title}</p>
                <p className="text-xs sm:text-sm text-text-secondary">وضعیت: {stream.status}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-text-secondary py-8 text-sm sm:text-base">استریمی وجود ندارد</p>
        )}
      </div>
    </div>
  )
}

