import { createContext, useContext, useState, useEffect } from 'react'

// Dark Mode Context
const DarkModeContext = createContext({
  darkMode: false,
  toggleDarkMode: () => {},
  setDarkMode: () => {},
})

/**
 * Dark Mode Provider Component
 * 
 * Provides dark mode state to all child components
 */
export function DarkModeProvider({ children }) {
  const [darkMode, setDarkMode] = useState(() => {
    // Get from localStorage or default to false
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('darkMode')
      return saved ? saved === 'true' : false
    }
    return false
  })

  useEffect(() => {
    // Apply dark mode class to document
    if (darkMode) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('darkMode', 'true')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('darkMode', 'false')
    }
  }, [darkMode])

  const toggleDarkMode = () => {
    setDarkMode(prev => !prev)
  }

  return (
    <DarkModeContext.Provider value={{ darkMode, toggleDarkMode, setDarkMode }}>
      {children}
    </DarkModeContext.Provider>
  )
}

/**
 * Custom hook for managing dark mode across the application
 * 
 * @returns {Object} { darkMode, toggleDarkMode, setDarkMode }
 */
export function useDarkMode() {
  const context = useContext(DarkModeContext)
  if (!context) {
    throw new Error('useDarkMode must be used within DarkModeProvider')
  }
  return context
}

