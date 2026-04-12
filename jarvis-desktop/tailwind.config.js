/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: '#0a0a0f',
          panel: '#1a1a2e',
          card: '#16213e',
          border: '#2a2a4a',
          primary: '#00d4ff',     // cyan
          accent: '#7c3aed',      // purple
          success: '#10b981',     // green
          danger: '#ff3366',
          warning: '#ffcc00',
          text: '#e0f0ff',
          textMuted: '#8892b0',
          glass: 'rgba(26, 26, 46, 0.7)',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 8s linear infinite',
        'wave': 'wave 1.5s ease-in-out infinite',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}
