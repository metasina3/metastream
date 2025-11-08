import { useDarkMode } from '../hooks/useDarkMode'
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline'

export default function DarkModeToggle({ className = '' }) {
  const { darkMode, toggleDarkMode } = useDarkMode()

  return (
    <button
      onClick={toggleDarkMode}
      className={`relative w-14 h-8 rounded-full transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 ${className}`}
      style={{
        background: darkMode 
          ? 'linear-gradient(135deg, #0C0E14 0%, #141821 100%)'
          : 'linear-gradient(135deg, #F4F7FB 0%, #EAF4FF 100%)',
        boxShadow: darkMode 
          ? '0 0 15px rgba(58, 231, 255, 0.3), inset 0 2px 4px rgba(0, 0, 0, 0.3)'
          : '0 0 15px rgba(0, 198, 255, 0.2), inset 0 2px 4px rgba(255, 255, 255, 0.3)',
      }}
      aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      <div
        className={`absolute top-1 left-1 w-6 h-6 rounded-full transition-all duration-300 flex items-center justify-center ${
          darkMode ? 'translate-x-6' : 'translate-x-0'
        }`}
        style={{
          background: darkMode
            ? 'linear-gradient(135deg, #3AE7FF 0%, #00C6FF 100%)'
            : 'linear-gradient(135deg, #FFD700 0%, #FFA500 100%)',
          boxShadow: darkMode
            ? '0 0 10px rgba(58, 231, 255, 0.6), 0 2px 4px rgba(0, 0, 0, 0.2)'
            : '0 0 10px rgba(255, 215, 0, 0.6), 0 2px 4px rgba(0, 0, 0, 0.1)',
        }}
      >
        {darkMode ? (
          <MoonIcon className="w-4 h-4 text-white" />
        ) : (
          <SunIcon className="w-4 h-4 text-white" />
        )}
      </div>
    </button>
  )
}

