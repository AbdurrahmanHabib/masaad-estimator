/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'ms-primary': '#2C3E50',
        'ms-glass': '#0077B6',
        'ms-accent': '#E67E22',
        'ms-bg': '#F8F9FA',
        'ms-dark': '#1A1A1A',
      },
      fontFamily: {
        sans: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}