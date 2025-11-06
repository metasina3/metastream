import { useState, useEffect } from 'react'
import { adminAPI } from '../../utils/api'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function AdminStats() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const loadStats = async () => {
    try {
      const response = await adminAPI.getStats()
      setStats(response.data)
    } catch (error) {
      console.error('Error loading stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12">در حال بارگذاری...</div>
  }

  const chartData = [
    { name: 'کاربران', value: stats?.total_users || 0 },
    { name: 'کانال‌ها', value: stats?.total_channels || 0 },
    { name: 'ویدیوها', value: stats?.total_videos || 0 },
    { name: 'استریم‌های زنده', value: stats?.live_streams || 0 },
  ]

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">آمار و گزارش‌ها</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">آمار کلی</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#0ea5e9" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">جزئیات</h3>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-600">کل کاربران:</span>
              <span className="font-bold">{stats?.total_users || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">کل کانال‌ها:</span>
              <span className="font-bold">{stats?.total_channels || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">کل ویدیوها:</span>
              <span className="font-bold">{stats?.total_videos || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">استریم‌های زنده:</span>
              <span className="font-bold">{stats?.live_streams || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">کل بازدیدکنندگان:</span>
              <span className="font-bold">{stats?.total_viewers || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">میانگین بازدید:</span>
              <span className="font-bold">{stats?.average_viewers_per_stream?.toFixed(2) || 0}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

