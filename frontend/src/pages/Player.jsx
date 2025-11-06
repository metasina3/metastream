import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { playerAPI, dashboardAPI } from '../utils/api'
import { 
  ChatBubbleLeftRightIcon, 
  UserGroupIcon,
  Bars3Icon,
  SunIcon,
  MoonIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import axios from 'axios'

export default function Player() {
  const { channelSlug } = useParams()  // This will be aparat_username
  const navigate = useNavigate()
  const [streamData, setStreamData] = useState(null)
  const [darkMode, setDarkMode] = useState(() => {
    // Get from localStorage or default to false
    const saved = localStorage.getItem('darkMode')
    return saved ? saved === 'true' : false
  })
  const [showMenu, setShowMenu] = useState(false)
  const [showRegisterModal, setShowRegisterModal] = useState(false)
  const [comments, setComments] = useState([])
  const [newComment, setNewComment] = useState('')
  const [viewerCount, setViewerCount] = useState(0)
  const [lastCommentId, setLastCommentId] = useState(0)
  const [loading, setLoading] = useState(true)
  const [streamStatus, setStreamStatus] = useState(null) // 'countdown' | 'preparing' | 'live' | 'ended' | 'next'
  const [countdown, setCountdown] = useState(null)
  const [channelOwner, setChannelOwner] = useState(null)
  
  const heartbeatIntervalRef = useRef(null)
  const pollingIntervalRef = useRef(null)
  const commentQueueRef = useRef([])
  const viewerNameRef = useRef(null)
  const viewerPhoneRef = useRef(null)
  const viewerIdRef = useRef(null)
  const preparingTimeoutRef = useRef(null)

  // Load or create viewer ID from cookie (GLOBAL - not per channel)
  useEffect(() => {
    // Use global cookie names (not per-channel)
    const viewerIdCookieName = `viewer_id` // Global viewer ID
    const viewerDataCookieName = `viewer_data` // Global viewer data
    
    // Check for existing viewer ID (global)
    const idCookie = document.cookie.split(';').find(c => c.trim().startsWith(`${viewerIdCookieName}=`))
    if (idCookie) {
      viewerIdRef.current = idCookie.split('=')[1]
      console.log('[Player] Loaded existing global viewer ID:', viewerIdRef.current)
    } else {
      // Create new unique viewer ID (global)
      const newId = `viewer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      viewerIdRef.current = newId
      // Store in cookie (4 months expiry)
      const expires = new Date(Date.now() + 4 * 30 * 24 * 60 * 60 * 1000).toUTCString()
      document.cookie = `${viewerIdCookieName}=${newId}; expires=${expires}; path=/; SameSite=Lax`
      console.log('[Player] Created new global viewer ID:', newId)
    }
    
    // Load viewer registration data from global cookie
    const dataCookie = document.cookie.split(';').find(c => c.trim().startsWith(`${viewerDataCookieName}=`))
    if (dataCookie) {
      try {
        const value = dataCookie.split('=')[1]
        const data = JSON.parse(decodeURIComponent(value))
        viewerNameRef.current = data.name
        viewerPhoneRef.current = data.phone
        console.log('[Player] Loaded global viewer data:', data.name)
      } catch (e) {
        console.error('Error parsing viewer cookie:', e)
      }
    }
  }, []) // No dependency on channelSlug - global cookie

  // Load initial data
  useEffect(() => {
    loadPlayerData()
    
    return () => {
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current)
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current)
    }
  }, [channelSlug])

  // Apply dark mode
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('darkMode', 'true')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('darkMode', 'false')
    }
  }, [darkMode])

  // Start heartbeat and polling for all active stream states
  useEffect(() => {
    const streamId = streamData?.stream?.id
    const status = streamStatus
    
    // Start heartbeat/polling for: countdown, preparing, live
    // Don't start for: ended (more than 5 min), no_stream, null
    const activeStatuses = ['countdown', 'preparing', 'live', 'ended']
    
    if (!streamId || !activeStatuses.includes(status)) {
      console.log('[Player] Not starting heartbeat/polling:', { streamId, status })
      return
    }
    
    // For ended status, only if within 5 minutes
    if (status === 'ended' && streamData?.stream?.ended_at) {
      const endedAt = new Date(streamData.stream.ended_at)
      const now = new Date()
      const minutesSinceEnd = (now - endedAt) / 1000 / 60
      if (minutesSinceEnd > 5) {
        console.log('[Player] Stream ended more than 5 minutes ago, not starting heartbeat')
        return
      }
    }
    
    console.log('[Player] Starting heartbeat and polling for stream:', streamId, 'status:', status)
    
    // Initial poll and heartbeat immediately
    pollUpdates(streamId)
    sendHeartbeat(streamId)
    
    // Heartbeat every 15 seconds
    heartbeatIntervalRef.current = setInterval(() => {
      sendHeartbeat(streamId)
    }, 15000)
    
    // Polling for comments and viewer count every 15 seconds
    pollingIntervalRef.current = setInterval(() => {
      pollUpdates(streamId)
    }, 15000)
    
    return () => {
      console.log('[Player] Cleaning up heartbeat and polling')
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current)
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current)
    }
  }, [streamData?.stream?.id, streamStatus])

  // Countdown timer logic and preparing state handler
  useEffect(() => {
    if (!streamData?.stream) {
      setCountdown(null)
      return
    }

    // Handle preparing state - check if timeout is done
    if (streamStatus === 'preparing' && preparingTimeoutRef.current) {
      // Timeout is already set, just wait for it
      return
    }

    // Handle scheduled status
    if (streamData.stream.status === 'scheduled') {
      const updateCountdown = () => {
        const startTime = new Date(streamData.stream.start_time)
        const now = new Date()
        const diff = startTime - now

        if (diff <= 0) {
          // Only set preparing if not already set and timeout not already scheduled
          if (streamStatus !== 'preparing' && !preparingTimeoutRef.current) {
            setStreamStatus('preparing')
            console.log('[Player] Stream start time reached, entering preparing state')
            // Wait 25 seconds before loading live stream - only once
            preparingTimeoutRef.current = setTimeout(async () => {
              console.log('[Player] Preparing period ended (25s), checking stream status')
              preparingTimeoutRef.current = null
              // Reload to get latest status from server
              try {
                const response = await playerAPI.getPlayer(channelSlug)
                const newStreamData = response.data
                
                // Always set to live after 25 seconds, regardless of server status
                console.log('[Player] 25 seconds passed, forcing live status')
                setStreamData(newStreamData)
                setStreamStatus('live')
                console.log('[Player] Status forced to live, player should render now')
              } catch (error) {
                console.error('[Player] Error reloading player data:', error)
                // Force set to live anyway
                setStreamStatus('live')
                console.log('[Player] Status forced to live after error')
              }
            }, 25000)
          }
          return
        }

        const hours = Math.floor(diff / (1000 * 60 * 60))
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
        const seconds = Math.floor((diff % (1000 * 60)) / 1000)

        setCountdown({ hours, minutes, seconds })
        setStreamStatus('countdown')
      }

      updateCountdown()
      const timer = setInterval(updateCountdown, 1000)

      return () => {
        clearInterval(timer)
      }
    } else {
      // Not scheduled - clear countdown
      setCountdown(null)
    }
  }, [streamData?.stream?.start_time, streamData?.stream?.status, streamStatus, channelSlug])

  // Separate effect to handle preparing timeout cleanup
  useEffect(() => {
    return () => {
      if (preparingTimeoutRef.current) {
        clearTimeout(preparingTimeoutRef.current)
        preparingTimeoutRef.current = null
      }
    }
  }, [])

  const loadPlayerData = async () => {
    try {
      setLoading(true)
      const response = await playerAPI.getPlayer(channelSlug)
      setStreamData(response.data)
      
      // Set channel owner name
      if (response.data.channel?.owner_name) {
        setChannelOwner(response.data.channel.owner_name)
      }
      
      // Don't show registration modal - let user watch stream freely
      // Registration will be requested inline when they try to comment
      
      // Set stream status based on server response
      if (response.data.stream) {
        const currentStatus = response.data.stream.status
        console.log('[Player] Stream status from server:', currentStatus)
        
        // Update allow_comments and clear comments if disabled
        if (response.data.stream.allow_comments !== undefined) {
          const newAllowComments = response.data.stream.allow_comments
          const oldAllowComments = streamData?.stream?.allow_comments
          
          if (oldAllowComments && !newAllowComments) {
            console.log('[Player] Comments disabled, clearing comments')
            setComments([])
            setLastCommentId(0)
          }
        }
        
        if (currentStatus === 'live') {
          console.log('[Player] Stream is live, setting status to live')
          setStreamStatus('live')
          // Clear any preparing timeout
          if (preparingTimeoutRef.current) {
            clearTimeout(preparingTimeoutRef.current)
            preparingTimeoutRef.current = null
          }
          // Ensure player renders
          console.log('[Player] Status set to live, player should render now')
        } else if (currentStatus === 'scheduled') {
          const startTime = new Date(response.data.stream.start_time)
          const now = new Date()
          const diff = startTime - now
          
          // If stream should have started (diff <= 0), wait for server to update it to live
          if (diff <= 0 && diff > -60000) { // Within 60 seconds of start time
            // Only set preparing if not already preparing to avoid infinite reload
            if (streamStatus !== 'preparing') {
              console.log('[Player] Stream should be starting soon, showing preparing message')
              setStreamStatus('preparing')
            }
          } else {
            setStreamStatus('countdown')
          }
        } else if (currentStatus === 'ended') {
          setStreamStatus('ended')
          // Check if there's a next stream
          if (response.data.next_stream) {
            setTimeout(() => {
              setStreamStatus('next')
              loadPlayerData()
            }, 300000) // 5 minutes
          }
        } else if (currentStatus === 'cancelled') {
          setStreamStatus('cancelled')
        }
      } else {
        // No stream found - show message
        setStreamStatus('no_stream')
      }
      
      setLoading(false)
    } catch (error) {
      console.error('Error loading player:', error)
      console.error('Error details:', error.response?.data)
      setLoading(false)
      // Show error message instead of generic "no stream"
      if (error.response?.status === 404) {
        setStreamStatus('channel_not_found')
      }
    }
  }

  const loadChannelOwner = async (userId) => {
    // This should call an API to get user name
    // For now, we'll use channel name
    if (streamData?.channel?.name) {
      setChannelOwner(streamData.channel.name)
    }
  }

  const sendHeartbeat = async (streamId) => {
    if (!streamId || !viewerIdRef.current) {
      console.warn('[Player] No stream ID or viewer ID for heartbeat')
      return
    }
    
    try {
      // Call Go service heartbeat endpoint
      const goServiceUrl = import.meta.env.VITE_API_URL || ''
      console.log('[Player] Sending heartbeat for stream:', streamId, 'viewer:', viewerIdRef.current)
      await axios.post(`${goServiceUrl}/heartbeat`, {
        stream_id: streamId,
        viewer_id: viewerIdRef.current  // Always use the unique viewer ID
      })
    } catch (error) {
      console.error('[Player] Heartbeat error:', error)
    }
  }

  const pollUpdates = async (streamId) => {
    if (!streamId) {
      console.warn('[Player] No stream ID for polling')
      return
    }
    
    try {
      const goServiceUrl = import.meta.env.VITE_API_URL || ''
      console.log('[Player] Polling updates for stream:', streamId, 'last_id:', lastCommentId)
      const response = await axios.post(`${goServiceUrl}/check-update`, {
        stream_id: streamId,
        last_id: lastCommentId || 0
      })

      console.log('[Player] Poll response:', response.data)

      // Always update viewer count from response
      if (response.data.online !== undefined) {
        console.log('[Player] Updating viewer count:', response.data.online)
        setViewerCount(response.data.online)
      }

      // Update allow_comments status from Go service - ALWAYS check this first
      if (response.data.allow_comments !== undefined) {
        const newAllowComments = response.data.allow_comments
        const oldAllowComments = streamData?.stream?.allow_comments
        
        console.log('[Player] Updating allow_comments from Go service:', newAllowComments, 'old:', oldAllowComments)
        
        // Always update streamData with allow_comments status
        setStreamData(prev => ({
          ...prev,
          stream: {
            ...prev?.stream,
            allow_comments: newAllowComments
          }
        }))
        
        // If comments are disabled, clear all comments immediately
        if (!newAllowComments) {
          console.log('[Player] Comments disabled, clearing all comments')
          setComments([])
          setLastCommentId(0)
          commentQueueRef.current = [] // Also clear the queue
          return // Don't process any comments if disabled
        }
        
        // If comments were just enabled (from disabled state), clear old comments
        if (oldAllowComments === false && newAllowComments === true) {
          console.log('[Player] Comments enabled, clearing old comments')
          setComments([])
          setLastCommentId(0)
        }
      }

      // Only process comments if allow_comments is true
      if (response.data.allow_comments === false) {
        console.log('[Player] Comments are disabled, skipping comment processing')
        return
      }

      // Process comments if:
      // 1. has_updates is true (new comments), OR
      // 2. Initial load (lastCommentId === 0) and comments exist
      const isInitialLoad = lastCommentId === 0
      const hasComments = response.data.comments && response.data.comments.length > 0
      
      if ((response.data.has_updates || isInitialLoad) && hasComments && response.data.allow_comments !== false) {
        // Add comments to queue for smooth display
        commentQueueRef.current.push(...response.data.comments)
        displayCommentsSmoothly(isInitialLoad)
        console.log('[Player] Processing comments:', response.data.comments.length, 'isInitialLoad:', isInitialLoad)
      }
    } catch (error) {
      console.error('[Player] Polling error:', error)
    }
  }

  const displayCommentsSmoothly = (isInitialLoad = false) => {
    // Display comments from queue
    if (commentQueueRef.current.length === 0) return

    // If initial load (lastCommentId === 0), show all comments at once
    // Otherwise, only show last 3 comments smoothly
    if (isInitialLoad || lastCommentId === 0) {
      // Initial load: show all comments at once
      const allComments = commentQueueRef.current.map(comment => ({
        id: comment.id,
        username: comment.username,
        message: comment.message,
        timestamp: comment.timestamp,
        isOwn: comment.username === viewerNameRef.current
      }))
      
      setComments(allComments)
      if (allComments.length > 0) {
        setLastCommentId(Math.max(...allComments.map(c => c.id)))
      }
      
      commentQueueRef.current = []
      console.log('[Player] Initial load: displayed', allComments.length, 'comments at once')
    } else {
      // New comments: only show last 3 smoothly
      const newComments = commentQueueRef.current.slice(-3) // Only last 3
      const totalComments = newComments.length
      const totalTime = 3000 // 3 seconds for last 3 comments
      const delayBetweenComments = totalTime / totalComments

      newComments.forEach((comment, index) => {
        setTimeout(() => {
          setComments(prev => {
            // Check if comment already exists
            const exists = prev.some(c => c.id === comment.id)
            if (exists) return prev
            
            const newComment = {
              id: comment.id,
              username: comment.username,
              message: comment.message,
              timestamp: comment.timestamp,
              isOwn: comment.username === viewerNameRef.current
            }
            return [...prev, newComment]
          })
          setLastCommentId(prev => Math.max(prev, comment.id))
        }, index * delayBetweenComments)
      })
      
      commentQueueRef.current = []
      console.log('[Player] New comments: displaying', newComments.length, 'comments smoothly')
    }
  }

  const handleRegister = async (name, phone) => {
    try {
      await playerAPI.enterStream(channelSlug, name, phone)
      viewerNameRef.current = name
      viewerPhoneRef.current = phone
      
      console.log('[Player] Registered viewer (global):', name)
      
      // Reload player data to update viewer status (cookie is set by backend)
      await loadPlayerData()
      
      // After reload, check if registration was successful
      // The viewer state should be updated by loadPlayerData
    } catch (error) {
      console.error('[Player] Registration error:', error)
      alert(error.response?.data?.detail || 'خطا در ثبت اطلاعات')
    }
  }

  const handleSubmitComment = async (e) => {
    e.preventDefault()
    if (!newComment.trim()) return

    try {
      console.log('[Player] Submitting comment:', newComment)
      const response = await playerAPI.submitComment(channelSlug, newComment)
      setNewComment('')
      
      // Show comment immediately to sender (pending status)
      if (response.data.comment) {
        const comment = response.data.comment
        const newCommentObj = {
          id: comment.id,
          username: comment.username,
          message: comment.message,
          timestamp: comment.timestamp,
          isOwn: true  // Mark as own comment
        }
        
        // Add to comments immediately
        setComments(prev => {
          // Check if already exists
          if (prev.some(c => c.id === comment.id)) return prev
          return [...prev, newCommentObj]
        })
        
        console.log('[Player] Comment submitted and shown immediately:', comment.id)
        
        // Schedule auto-approval check after 15 seconds
        setTimeout(() => {
          // Poll for updates to get approved comment
          if (streamData?.stream?.id) {
            pollUpdates(streamData.stream.id)
          }
        }, 16000) // 16 seconds to ensure approval
      }
      
      console.log('[Player] Comment submitted successfully')
    } catch (error) {
      console.error('[Player] Comment submission error:', error)
      alert(error.response?.data?.detail || 'خطا در ارسال نظر')
    }
  }

  const handleLogout = () => {
    // Delete global registration data cookie (keep viewer ID)
    const cookieName = `viewer_data` // Global cookie
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`
    viewerNameRef.current = null
    viewerPhoneRef.current = null
    console.log('[Player] Logged out viewer (global)')
    setShowMenu(false)
    loadPlayerData()
  }

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  // Render Aparat embed
  const renderAparatPlayer = () => {
    if (!streamData?.channel?.aparat_username) return null
    
    const aparatUsername = streamData.channel.aparat_username
    
    return (
      <div className="h_iframe-aparat_embed_frame" style={{position: 'relative'}}>
        <span style={{ display: 'block', paddingTop: '57%' }}></span>
        <iframe 
          scrolling="no" 
          allowFullScreen="true" 
          webkitallowfullscreen="true" 
          mozallowfullscreen="true"
          src={`https://www.aparat.com/embed/live/${aparatUsername}`}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%'
          }}
        />
      </div>
    )
  }

  if (loading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  // Show channel info even if no stream
  if (streamStatus === 'channel_not_found') {
    return (
      <div className={`min-h-screen flex items-center justify-center ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4 text-red-500">کانال پیدا نشد</h1>
          <p className="text-gray-500">لطفا آدرس را بررسی کنید</p>
        </div>
      </div>
    )
  }

  if (streamStatus === 'cancelled') {
    return (
      <div className={`min-h-screen flex items-center justify-center ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4 text-orange-500">استریم لغو شده</h1>
          {streamData?.stream?.error_message && (
            <p className="text-red-500 mb-2">{streamData.stream.error_message}</p>
          )}
          <p className="text-gray-500 mb-2">این استریم لغو شده است</p>
          <p className="text-sm text-gray-400">لطفا استریم دیگری را انتخاب کنید</p>
        </div>
      </div>
    )
  }

  if (streamStatus === 'no_stream' && streamData?.channel) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">کانال: {streamData.channel.owner_name || streamData.channel.name}</h1>
          <p className="text-gray-500 mb-2">در حال حاضر استریمی فعال نیست</p>
          <p className="text-sm text-gray-400">لطفا بعدا تلاش کنید</p>
        </div>
      </div>
    )
  }

  if (!streamData) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">خطا در بارگذاری</h1>
          <p className="text-gray-500">لطفا دوباره تلاش کنید</p>
        </div>
      </div>
    )
  }

  const isMobile = window.innerWidth < 1024

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
      {/* Header */}
      <header className={`sticky top-0 z-50 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-md`}>
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          {/* Left: Hamburger Menu + Live Indicator */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <Bars3Icon className="w-6 h-6" />
              </button>
              
              {showMenu && (
                <>
                  {/* Overlay */}
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowMenu(false)}
                  />
                  {/* Menu */}
                  <div className={`absolute right-0 top-full mt-2 w-48 rounded-lg shadow-lg z-50 ${darkMode ? 'bg-gray-800' : 'bg-white'} border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                    <button
                      onClick={handleLogout}
                      className="w-full text-right px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                    >
                      <XMarkIcon className="w-4 h-4" />
                      خروج
                    </button>
                    <button
                      onClick={toggleDarkMode}
                      className="w-full text-right px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                    >
                      {darkMode ? <SunIcon className="w-4 h-4" /> : <MoonIcon className="w-4 h-4" />}
                      {darkMode ? 'حالت روشن' : 'حالت تاریک'}
                    </button>
                  </div>
                </>
              )}
            </div>
            
            {/* Live Indicator */}
            {streamStatus && (
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full animate-pulse ${
                  streamStatus === 'countdown' || streamStatus === 'preparing' ? 'bg-yellow-500' :
                  streamStatus === 'live' ? 'bg-red-500' :
                  streamStatus === 'ended' ? 'bg-orange-500' :
                  'bg-gray-400'
                }`}></div>
                <span className="text-xs font-medium">
                  {streamStatus === 'countdown' ? 'در انتظار' :
                   streamStatus === 'preparing' ? 'در حال آماده‌سازی' :
                   streamStatus === 'live' ? 'زنده' :
                   streamStatus === 'ended' ? 'پایان یافته' :
                   'آفلاین'}
                </span>
              </div>
            )}
          </div>

          {/* Center: Logo and Channel Owner */}
          <div className="flex items-center gap-3">
            <a href={import.meta.env.VITE_MAIN_URL || '#'} className="flex items-center gap-2">
              <img src="/logo.png" alt="Meta Stream" className="w-8 h-8" />
            </a>
            {channelOwner && (
              <span className="font-semibold">{channelOwner}</span>
            )}
          </div>

          {/* Right: Empty for balance */}
          <div className="w-10"></div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {isMobile ? (
          // Mobile Layout
          <div className="space-y-6">
            {/* Player */}
            <div className={`rounded-lg overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-black'}`}>
              {streamStatus === 'countdown' && countdown ? (
                <div className="aspect-video flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-4xl font-bold mb-2">
                      {String(countdown.hours).padStart(2, '0')}:
                      {String(countdown.minutes).padStart(2, '0')}:
                      {String(countdown.seconds).padStart(2, '0')}
                    </div>
                    <p className="text-lg">تا شروع پخش زنده</p>
                  </div>
                </div>
              ) : streamStatus === 'preparing' ? (
                <div className="aspect-video flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-lg mb-2">لایو در حال آماده‌سازی است</p>
                    <p className="text-sm text-gray-400">لطفاً صبر کنید، پخش به زودی شروع می‌شود</p>
                    <p className="text-xs text-gray-500 mt-2">⏱️ تا شروع پخش چند لحظه صبر کنید</p>
                  </div>
                </div>
              ) : streamStatus === 'ended' ? (
                <div className="aspect-video flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-lg">پخش زنده به پایان رسید</p>
                  </div>
                </div>
              ) : streamStatus === 'live' ? (
                <div className="aspect-video" key={`player-${streamData?.stream?.id}-${streamStatus}`}>
                  {streamData?.channel?.aparat_username ? (
                    renderAparatPlayer()
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                      <p className="ml-3 text-gray-500">در حال بارگذاری پلیر...</p>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* Title and Caption */}
            {streamData.stream && (
              <div className={`rounded-lg p-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h1 className="text-xl font-bold mb-2">{streamData.stream.title}</h1>
                    {streamData.stream.caption && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">{streamData.stream.caption}</p>
                    )}
                  </div>
                  {/* Cancel button for live streams - will be shown to channel owner */}
                  {streamStatus === 'live' && streamData.is_owner && (
                    <button
                      onClick={async () => {
                        if (confirm('آیا مطمئن هستید که می‌خواهید استریم را لغو کنید؟')) {
                          try {
                            await dashboardAPI.cancelStream(streamData.stream.id)
                            alert('استریم لغو شد')
                            loadPlayerData()
                          } catch (error) {
                            alert(error.response?.data?.detail || 'خطا در لغو استریم')
                          }
                        }
                      }}
                      className="ml-2 px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 transition-colors"
                    >
                      ❌ لغو استریم
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Comments */}
            <CommentsSection
              stream={streamData.stream}
              viewer={streamData.viewer}
              comments={comments}
              newComment={newComment}
              setNewComment={setNewComment}
              onSubmitComment={handleSubmitComment}
              onRegister={handleRegister}
              viewerCount={viewerCount}
              darkMode={darkMode}
            />
          </div>
        ) : (
          // Desktop Layout
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Player Section (Right) */}
            <div className="lg:col-span-2 space-y-4">
              {/* Player */}
              <div className={`rounded-lg overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-black'}`}>
                {streamStatus === 'countdown' && countdown ? (
                  <div className="aspect-video flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-6xl font-bold mb-4">
                        {String(countdown.hours).padStart(2, '0')}:
                        {String(countdown.minutes).padStart(2, '0')}:
                        {String(countdown.seconds).padStart(2, '0')}
                      </div>
                      <p className="text-xl">تا شروع پخش زنده</p>
                    </div>
                  </div>
                ) : streamStatus === 'preparing' ? (
                  <div className="aspect-video flex items-center justify-center">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
                      <p className="text-xl mb-2">لایو در حال آماده‌سازی است</p>
                      <p className="text-sm text-gray-400">لطفاً صبر کنید، پخش به زودی شروع می‌شود</p>
                      <p className="text-xs text-gray-500 mt-2">⏱️ تا شروع پخش چند لحظه صبر کنید</p>
                    </div>
                  </div>
                ) : streamStatus === 'ended' ? (
                  <div className="aspect-video flex items-center justify-center">
                    <div className="text-center">
                      <p className="text-xl">پخش زنده به پایان رسید</p>
                    </div>
                  </div>
                ) : streamStatus === 'live' ? (
                  <div className="aspect-video">
                    {renderAparatPlayer()}
                  </div>
                ) : null}
              </div>

              {/* Title and Caption */}
              {streamData.stream && (
                <div className={`rounded-lg p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h1 className="text-2xl font-bold mb-2">{streamData.stream.title}</h1>
                      {streamData.stream.caption && (
                        <p className="text-gray-600 dark:text-gray-400">{streamData.stream.caption}</p>
                      )}
                    </div>
                    {/* Cancel button for live streams - will be shown to channel owner */}
                    {streamStatus === 'live' && streamData.is_owner && (
                      <button
                        onClick={async () => {
                          if (confirm('آیا مطمئن هستید که می‌خواهید استریم را لغو کنید؟')) {
                            try {
                              await dashboardAPI.cancelStream(streamData.stream.id)
                              alert('استریم لغو شد')
                              loadPlayerData()
                            } catch (error) {
                              alert(error.response?.data?.detail || 'خطا در لغو استریم')
                            }
                          }
                        }}
                        className="ml-2 px-4 py-2 bg-red-500 text-white text-sm rounded hover:bg-red-600 transition-colors"
                      >
                        ❌ لغو استریم
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Comments Section (Left) */}
            <CommentsSection
              stream={streamData.stream}
              viewer={streamData.viewer}
              comments={comments}
              newComment={newComment}
              setNewComment={setNewComment}
              onSubmitComment={handleSubmitComment}
              onRegister={handleRegister}
              viewerCount={viewerCount}
              darkMode={darkMode}
            />
          </div>
        )}
      </div>

      {/* Registration Modal - Removed, now inline in comment section */}
    </div>
  )
}

// Comments Section Component
function CommentsSection({ stream, viewer, comments, newComment, setNewComment, onSubmitComment, onRegister, viewerCount, darkMode }) {
  const commentsEndRef = useRef(null)
  const [localName, setLocalName] = useState('')
  const [localPhone, setLocalPhone] = useState('')
  const [showRegForm, setShowRegForm] = useState(false)
  
  // Close registration form when viewer is registered
  useEffect(() => {
    if (viewer && !viewer.needs_registration) {
      setShowRegForm(false)
    }
  }, [viewer])

  // Auto-scroll disabled to prevent page scroll on mobile
  // useEffect(() => {
  //   commentsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  // }, [comments])

  if (!stream) return null

  return (
    <div className={`rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} flex flex-col h-[600px]`}>
      {/* Header with Viewer Count */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <ChatBubbleLeftRightIcon className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold">گفتگوی زنده</h2>
          </div>
          <div className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
            <UserGroupIcon className="w-4 h-4" />
            <span>{viewerCount} بیننده</span>
          </div>
        </div>
      </div>

      {/* Comments List */}
      {stream.allow_comments ? (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {comments.length === 0 ? (
              <p className="text-center text-gray-400 py-8">هنوز نظری وجود ندارد</p>
            ) : (
              comments.map((comment) => (
                <div
                  key={comment.id}
                  className={`flex ${comment.isOwn ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      comment.isOwn
                        ? darkMode
                          ? 'bg-primary-600 text-white'
                          : 'bg-primary-100 text-primary-900'
                        : darkMode
                        ? 'bg-gray-700 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className={`font-medium text-sm mb-1 ${
                      comment.isOwn
                        ? darkMode
                          ? 'text-primary-200'
                          : 'text-primary-700'
                        : darkMode
                        ? 'text-blue-300'
                        : 'text-blue-600'
                    }`}>{comment.username}</p>
                    <p className="text-sm">{comment.message}</p>
                    <p className="text-xs opacity-70 mt-1">
                      {new Date(comment.timestamp).toLocaleTimeString('fa-IR')}
                    </p>
                  </div>
                </div>
              ))
            )}
            <div ref={commentsEndRef} />
          </div>

          {/* Comment Input or Registration Form */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            {(!viewer || viewer?.needs_registration) && !showRegForm ? (
              // Show registration prompt - always show if needs registration or viewer is null
              <div className="text-center space-y-3">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  برای ارسال نظر، لطفاً ثبت‌نام کنید
                </p>
                <button
                  onClick={() => setShowRegForm(true)}
                  className="w-full bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
                >
                  ثبت‌نام
                </button>
              </div>
            ) : (!viewer || viewer?.needs_registration) && showRegForm ? (
              // Inline registration form
              <div className="space-y-3">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  نام و شماره همراه خود را وارد کنید:
                </p>
                <input
                  type="text"
                  placeholder="نام"
                  value={localName}
                  onChange={(e) => setLocalName(e.target.value)}
                  className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-primary-500 ${
                    darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'
                  }`}
                />
                <input
                  type="tel"
                  placeholder="شماره همراه (09XXXXXXXXX)"
                  value={localPhone}
                  onChange={(e) => {
                    // Only allow numbers and format
                    const value = e.target.value.replace(/[^0-9]/g, '')
                    setLocalPhone(value)
                  }}
                  maxLength={11}
                  className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-primary-500 ${
                    darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'
                  }`}
                  dir="ltr"
                />
                {localPhone && !localPhone.startsWith('09') && (
                  <p className="text-xs text-red-500">شماره باید با 09 شروع شود</p>
                )}
                {localPhone && localPhone.length !== 11 && localPhone.length > 0 && (
                  <p className="text-xs text-red-500">شماره باید 11 رقم باشد</p>
                )}
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      // Validate phone number
                      if (!localName || !localPhone) {
                        alert('لطفاً نام و شماره همراه را وارد کنید')
                        return
                      }
                      if (!localPhone.startsWith('09')) {
                        alert('شماره همراه باید با 09 شروع شود')
                        return
                      }
                      if (localPhone.length !== 11) {
                        alert('شماره همراه باید 11 رقم باشد')
                        return
                      }
                      // Don't close form here - let useEffect handle it after registration
                      onRegister(localName, localPhone)
                    }}
                    className="flex-1 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
                  >
                    ثبت
                  </button>
                  <button
                    onClick={() => setShowRegForm(false)}
                    className={`px-4 py-2 border rounded-lg ${
                      darkMode
                        ? 'border-gray-600 hover:bg-gray-700'
                        : 'border-gray-300 hover:bg-gray-100'
                    }`}
                  >
                    انصراف
                  </button>
                </div>
              </div>
            ) : (
              // Comment input form
              <form onSubmit={onSubmitComment}>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="نظر خود را بنویسید..."
                    className={`flex-1 px-3 py-2 rounded-lg border ${
                      darkMode
                        ? 'bg-gray-700 border-gray-600 text-white'
                        : 'bg-white border-gray-300'
                    }`}
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  >
                    ارسال
                  </button>
                </div>
              </form>
            )}
          </div>
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center p-8">
          <p className="text-center text-gray-500 dark:text-gray-400">
            گفت‌وگو برای این لایو غیرفعال است
          </p>
        </div>
      )}
    </div>
  )
}

// Registration Modal Component
function RegisterModal({ onRegister, onClose }) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [lastName, setLastName] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim() || !phone.trim()) {
      alert('لطفا نام و شماره همراه را وارد کنید')
      return
    }

    setLoading(true)
    try {
      await onRegister(name, phone)
    } catch (error) {
      alert(error.response?.data?.detail || 'خطا در ثبت اطلاعات')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-2xl font-bold mb-4">ورود به پخش زنده</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          برای ثبت نظر، لطفا اطلاعات خود را وارد کنید
        </p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">نام *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input w-full"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">نام خانوادگی (اختیاری)</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="input w-full"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">شماره همراه *</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="input w-full"
              placeholder="09123456789"
              required
            />
          </div>
          
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
              disabled={loading}
            >
              انصراف
            </button>
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={loading}
            >
              {loading ? 'در حال ثبت...' : 'ثبت'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
