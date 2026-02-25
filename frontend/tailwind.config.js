/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        'ms-bg': '#f8fafc',      // Light Slate background
        'ms-sidebar': '#1e293b',  // Dark Navy sidebar
        'ms-primary': '#2563eb',  // Vibrant Blue
        'ms-emerald': '#10b981', // Vibrant Green
        'ms-red': '#ef4444',     // Vibrant Red
        'ms-amber': '#f59e0b',   // Vibrant Amber
        'ms-border': '#e2e8f0',  // Light border
      },
      fontFamily: {
        sans: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'erp': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
      }
    },
  },
  plugins: [],
}