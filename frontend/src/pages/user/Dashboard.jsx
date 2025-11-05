import { useState, useEffect } from 'react'
import { dashboardAPI } from '../../utils/api'
import { Link } from 'react-router-dom'
import { VideoCameraIcon, FilmIcon, CalendarIcon } from '@heroicons/react/24/outline'

export default function UserDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
    
    // Auto-refresh every 10 seconds (silent)
    const interval = setInterval(() => {
      loadDashboard(false) // silent refresh
    }, 10000)
    
    return () => clearInterval(interval)
  }, [])

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

  if (loading) {
    return <div className="text-center py-12">در حال بارگذاری...</div>
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">داشبورد کاربری</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Link to="/dashboard/channels" className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm mb-2">کانال‌ها</p>
              <p className="text-3xl font-bold">{data?.channels?.length || 0}</p>
            </div>
            <VideoCameraIcon className="w-12 h-12 text-primary-600" />
          </div>
        </Link>
        
        <Link to="/dashboard/videos" className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm mb-2">ویدیوها</p>
              <p className="text-3xl font-bold">{data?.videos?.length || 0}</p>
            </div>
            <FilmIcon className="w-12 h-12 text-primary-600" />
          </div>
        </Link>
        
        <Link to="/dashboard/streams" className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm mb-2">استریم‌ها</p>
              <p className="text-3xl font-bold">{data?.streams?.length || 0}</p>
            </div>
            <CalendarIcon className="w-12 h-12 text-primary-600" />
          </div>
        </Link>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold mb-4">استریم‌های اخیر</h2>
        {data?.streams?.length > 0 ? (
          <div className="space-y-2">
            {data.streams.slice(0, 5).map((stream) => (
              <div key={stream.id} className="border rounded-lg p-4">
                <p className="font-medium">{stream.title}</p>
                <p className="text-sm text-gray-500">وضعیت: {stream.status}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-gray-500 py-8">استریمی وجود ندارد</p>
        )}
      </div>
    </div>
  )
}

