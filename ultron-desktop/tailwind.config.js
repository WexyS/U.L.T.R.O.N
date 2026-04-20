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
        'ultron-bg': 'rgb(var(--color-bg) / <alpha-value>)',
        'ultron-bg-secondary': 'rgb(var(--color-bg-secondary) / <alpha-value>)',
        'ultron-bg-tertiary': 'rgb(var(--color-bg-tertiary) / <alpha-value>)',
        'ultron-panel': 'rgb(var(--color-panel) / <alpha-value>)',
        'ultron-card': 'rgb(var(--color-card) / <alpha-value>)',
        'ultron-border': 'rgb(var(--color-border) / <alpha-value>)',
        'ultron-border-light': 'rgb(var(--color-border-light) / <alpha-value>)',
        'ultron-text': 'rgb(var(--color-text) / <alpha-value>)',
        'ultron-text-secondary': 'rgb(var(--color-text-secondary) / <alpha-value>)',
        'ultron-text-tertiary': 'rgb(var(--color-text-tertiary) / <alpha-value>)',
        'ultron-text-muted': 'rgb(var(--color-text-muted) / <alpha-value>)',
        'ultron-accent': 'rgb(var(--color-accent) / <alpha-value>)',
        'ultron-accent-hover': 'rgb(var(--color-accent-hover) / <alpha-value>)',
        'ultron-success': 'rgb(var(--color-success) / <alpha-value>)',
        'ultron-warning': 'rgb(var(--color-warning) / <alpha-value>)',
        'ultron-danger': 'rgb(var(--color-danger) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'sans-serif'],
        mono: ['SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'monospace'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
