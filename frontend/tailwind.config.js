/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        'ms-bg': '#f8fafc',
        'ms-sidebar': '#0f172a',
        'ms-primary': '#1e3a5f',
        'ms-accent': '#3b82f6',
        'ms-emerald': '#10b981',
        'ms-green': '#00bf63',
        'ms-purple': '#8b5cf6',
        'ms-red': '#ef4444',
        'ms-amber': '#f59e0b',
        'ms-border': '#e2e8f0',
        'ms-text': '#374151',
        'ms-text-light': '#64748b',
        'ms-navy': '#0f172a',
        'ms-blue': '#1e3a5f',
      },
      fontFamily: {
        sans: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'erp': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.04)',
      },
      borderRadius: {
        'card': '12px',
      }
    },
  },
  plugins: [],
}
