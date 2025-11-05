import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import Layout from './components/Layout'
import Login from './pages/Login'
import AdminDashboard from './pages/admin/Dashboard'
import AdminUsers from './pages/admin/Users'
import AdminStats from './pages/admin/Stats'
import AdminModeration from './pages/admin/Moderation'
import AdminApprovals from './pages/admin/Approvals'
import UserDashboard from './pages/user/Dashboard'
import UserChannels from './pages/user/Channels'
import UserVideos from './pages/user/Videos'
import UserStreams from './pages/user/Streams'
import Player from './pages/Player'

function AppContent() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/c/:channelSlug" element={<Player />} />
      
      {/* Protected Routes */}
      <Route element={<Layout />}>
        {user?.role === 'admin' ? (
          <>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/approvals" element={<AdminApprovals />} />
            <Route path="/admin/stats" element={<AdminStats />} />
            <Route path="/admin/moderation" element={<AdminModeration />} />
          </>
        ) : (
          <>
            <Route path="/dashboard" element={<UserDashboard />} />
            <Route path="/dashboard/channels" element={<UserChannels />} />
            <Route path="/dashboard/videos" element={<UserVideos />} />
            <Route path="/dashboard/streams" element={<UserStreams />} />
            <Route path="/dashboard/moderation" element={<AdminModeration />} />
          </>
        )}
        
        <Route path="/" element={<Navigate to={user?.role === 'admin' ? '/admin' : '/dashboard'} replace />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
