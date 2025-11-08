/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00C6FF',
          light: '#3AE7FF',
          dark: '#00B2FF',
        },
        secondary: {
          DEFAULT: '#7B2FF7',
          light: '#8A4FFF',
        },
        accent: {
          DEFAULT: '#3AE7FF',
          hover: '#00C6FF',
        },
        error: {
          DEFAULT: '#FF4B91',
        },
        bg: {
          DEFAULT: 'var(--bg-background)',
          surface: 'var(--bg-surface)',
          glass: 'var(--bg-glass)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
        },
        border: {
          DEFAULT: 'var(--border-color)',
          glow: 'var(--border-glow)',
        },
      },
      backgroundImage: {
        'gradient-primary': 'var(--primary-gradient)',
        'gradient-primary-light': 'var(--primary-gradient-light)',
        'gradient-glow': 'var(--gradient-glow)',
        'gradient-bg-light': 'var(--bg-gradient-light)',
        'gradient-bg-dark': 'var(--bg-gradient-dark)',
      },
      boxShadow: {
        'glow': 'var(--shadow-glow)',
        'glow-lg': 'var(--shadow-glow-lg)',
        'glow-purple': 'var(--shadow-glow-purple)',
        'glow-accent': 'var(--shadow-glow-accent)',
        'glass': 'var(--shadow-glass)',
        'neon': 'var(--shadow-neon)',
      },
      backdropBlur: {
        xs: '2px',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(0, 198, 255, 0.3)' },
          '50%': { boxShadow: '0 0 30px rgba(0, 198, 255, 0.6)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
      },
    },
  },
  plugins: [],
}

