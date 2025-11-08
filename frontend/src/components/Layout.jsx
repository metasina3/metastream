import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import { 
  HomeIcon, 
  UserGroupIcon, 
  ChartBarIcon, 
  ChatBubbleLeftRightIcon,
  VideoCameraIcon,
  RectangleStackIcon,
  FilmIcon,
  CalendarIcon,
  Bars3Icon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import { adminAPI } from '../utils/api'
import Logo from './Logo.jsx'
import DarkModeToggle from './DarkModeToggle'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const isAdmin = user?.role === 'admin'

  const adminNavItems = [
    { path: '/admin', label: 'داشبورد', icon: HomeIcon },
    { path: '/admin/users', label: 'کاربران', icon: UserGroupIcon },
    { path: '/admin/approvals', label: 'درخواست‌ها', icon: RectangleStackIcon },
    { path: '/admin/stats', label: 'آمار', icon: ChartBarIcon },
    { path: '/admin/moderation', label: 'مدیریت نظرات', icon: ChatBubbleLeftRightIcon },
  ]

  const userNavItems = [
    { path: '/dashboard', label: 'داشبورد', icon: HomeIcon },
    { path: '/dashboard/channels', label: 'کانال‌ها', icon: VideoCameraIcon },
    { path: '/dashboard/videos', label: 'ویدیوها', icon: FilmIcon },
    { path: '/dashboard/streams', label: 'استریم‌ها', icon: CalendarIcon },
  ]

  const navItems = isAdmin ? adminNavItems : userNavItems

  return (
    <div className="min-h-screen relative">
      {/* Dark Mode Toggle - Top Left */}
      <div className="fixed top-6 left-6 z-50">
        <DarkModeToggle />
      </div>
      
      {/* Mobile Menu Button */}
      {isMobile && (
        <button
          onClick={() => setSidebarOpen(true)}
          className="fixed top-4 right-4 z-50 p-2 glass rounded-xl shadow-glass hover:shadow-glow border border-border transition-all duration-300"
        >
          <Bars3Icon className="w-6 h-6 text-text-primary" />
        </button>
      )}

      {/* Sidebar Overlay (Mobile) - Blur Background */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-md z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed right-0 top-0 h-full w-64 z-50 transition-transform duration-300 border-l border-border ${
        isMobile ? (sidebarOpen ? 'translate-x-0' : 'translate-x-full') : 'translate-x-0'
      }`}
      style={{
        background: 'var(--bg-surface)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        boxShadow: 'var(--shadow-glass)',
      }}>
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Logo size="sm" showText={false} />
              <div>
                <h1 className="text-xl font-bold text-gradient">MetaStream</h1>
                <p className="text-xs text-text-secondary mt-0.5">{isAdmin ? 'پنل مدیریت' : 'پنل کاربری'}</p>
              </div>
            </div>
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-2 hover:bg-bg rounded-lg transition-colors"
              >
                <XMarkIcon className="w-6 h-6 text-text-primary" />
              </button>
            )}
          </div>
        </div>
        
        <nav className="p-4 overflow-y-auto">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => isMobile && setSidebarOpen(false)}
              className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-bg transition-colors mb-2 text-text-primary group"
            >
              <item.icon className="w-5 h-5 flex-shrink-0 text-text-secondary group-hover:text-accent transition-colors" />
              <span className="text-sm">{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-0 w-full p-4 border-t border-border glass">
          <div className="mb-4">
            <p className="text-sm font-medium text-text-primary">{user?.name || 'کاربر'}</p>
            <p className="text-xs text-text-secondary">{user?.phone}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full btn-secondary text-sm"
          >
            خروج
          </button>
        </div>
      </aside>

      {/* Impersonation banner */}
      {user?.impersonating && (
        <div className={`${isMobile ? 'mr-0' : 'mr-64'}`}>
          <div className="bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 px-4 py-3 flex items-center justify-between flex-wrap gap-2 border-b border-amber-200 dark:border-amber-800">
            <span className="text-sm">شما در حالت ورود به کاربر هستید</span>
            <button
              className="btn-secondary text-xs px-3 py-1"
              onClick={async () => {
                try {
                  await adminAPI.revertImpersonation()
                  window.location.replace('/admin')
                } catch (e) {}
              }}
            >
              خروج از این حالت
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className={`${isMobile ? 'mr-0 p-4 pt-20' : 'mr-64 p-8 pt-6'}`}>
        <Outlet />
      </main>
    </div>
  )
}

