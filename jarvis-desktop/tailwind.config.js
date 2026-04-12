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
        'jarvis-bg': 'var(--color-bg)',
        'jarvis-bg-secondary': 'var(--color-bg-secondary)',
        'jarvis-bg-tertiary': 'var(--color-bg-tertiary)',
        'jarvis-panel': 'var(--color-panel)',
        'jarvis-card': 'var(--color-card)',
        'jarvis-border': 'var(--color-border)',
        'jarvis-border-light': 'var(--color-border-light)',
        'jarvis-text': 'var(--color-text)',
        'jarvis-text-secondary': 'var(--color-text-secondary)',
        'jarvis-text-tertiary': 'var(--color-text-tertiary)',
        'jarvis-text-muted': 'var(--color-text-muted)',
        'jarvis-accent': 'var(--color-accent)',
        'jarvis-accent-hover': 'var(--color-accent-hover)',
        'jarvis-success': 'var(--color-success)',
        'jarvis-warning': 'var(--color-warning)',
        'jarvis-danger': 'var(--color-danger)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
      },
    },
  },
  plugins: [],
}
