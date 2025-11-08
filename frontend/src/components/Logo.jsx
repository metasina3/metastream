/**
 * MetaStream Logo Component
 * 
 * Uses logo files based on dark/light mode
 */

import React from 'react'
import { useDarkMode } from '../hooks/useDarkMode'

export default function Logo({ size = 'md', showText = true, className = '' }) {
  const { darkMode } = useDarkMode()
  
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
  }

  const textSizeClasses = {
    sm: 'text-lg',
    md: 'text-xl',
    lg: 'text-2xl',
    xl: 'text-4xl',
  }

  // Select logo based on dark mode
  const logoPath = darkMode ? '/logo-dark.png' : '/logo-light.png'

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Logo Image */}
      <img 
        src={logoPath}
        alt="MetaStream Logo" 
        className={`${sizeClasses[size]} object-contain flex-shrink-0`}
        loading="eager"
        onError={(e) => {
          // Fallback to default logo if specific mode logo fails
          e.target.src = '/logo.png'
        }}
      />

      {/* Logo Text */}
      {showText && (
        <div className="flex flex-col">
          <h1 className={`${textSizeClasses[size]} font-bold text-gradient`}>
            MetaStream
          </h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Streaming Platform
          </p>
        </div>
      )}
    </div>
  )
}

