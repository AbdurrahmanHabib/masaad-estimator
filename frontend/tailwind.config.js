/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'ms-primary': '#2C3E50',
        'ms-glass': '#0077B6',
        'ms-accent': '#E67E22',
        'ms-bg': '#F8F9FA',
        'ms-dark': '#020617',
        'ms-emerald': '#10b981',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}