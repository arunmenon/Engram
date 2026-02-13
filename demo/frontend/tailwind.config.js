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
        surface: {
          DEFAULT: '#16161a',
          dark: '#0f0f11',
          darker: '#0a0a0c',
          card: '#1e1e24',
          hover: '#252530',
        },
        accent: {
          blue: '#3b82f6',
          green: '#22c55e',
          orange: '#f59e0b',
          red: '#ef4444',
          purple: '#a855f7',
          teal: '#14b8a6',
          amber: '#f59e0b',
        },
        muted: {
          DEFAULT: '#6b7280',
          light: '#9ca3af',
          dark: '#374151',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
