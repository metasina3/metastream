import { useState, useEffect } from 'react'
import { adminAPI } from '../../utils/api'
import { ChartBarIcon, UserGroupIcon, VideoCameraIcon, FilmIcon } from '@heroicons/react/24/outline'

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
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

  const cards = [
    {
      title: 'کل کاربران',
      value: stats?.total_users || 0,
      icon: UserGroupIcon,
      color: 'bg-blue-500',
    },
    {
      title: 'کل کانال‌ها',
      value: stats?.total_channels || 0,
      icon: VideoCameraIcon,
      color: 'bg-green-500',
    },
    {
      title: 'کل ویدیوها',
      value: stats?.total_videos || 0,
      icon: FilmIcon,
      color: 'bg-purple-500',
    },
    {
      title: 'استریم‌های زنده',
      value: stats?.live_streams || 0,
      icon: ChartBarIcon,
      color: 'bg-red-500',
    },
    {
      title: 'کل بازدیدکنندگان',
      value: stats?.total_viewers || 0,
      icon: ChartBarIcon,
      color: 'bg-yellow-500',
    },
    {
      title: 'میانگین بازدید',
      value: stats?.average_viewers_per_stream || 0,
      icon: ChartBarIcon,
      color: 'bg-indigo-500',
    },
  ]

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-bold mb-6 sm:mb-8">داشبورد مدیریت</h1>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {cards.map((card, index) => (
          <div key={index} className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-xs sm:text-sm mb-2">{card.title}</p>
                <p className="text-2xl sm:text-3xl font-bold">{card.value}</p>
              </div>
              <div className={`${card.color} p-3 sm:p-4 rounded-full text-white`}>
                <card.icon className="w-6 h-6 sm:w-8 sm:h-8" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

