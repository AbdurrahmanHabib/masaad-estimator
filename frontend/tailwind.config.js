/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        'ms-dark': '#020617',    // Slate-950
        'ms-panel': '#0f172a',   // Slate-900
        'ms-border': '#1e293b',  // Slate-800
        'ms-emerald': '#10b981', // Emerald-500
        'ms-amber': '#fbbf24',   // Amber-400 (Adjusted per requirement)
        'ms-slate-800': '#1e293b',
      },
      fontFamily: {
        sans: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      fontSize: {
        'xxs': '0.65rem',
      }
    },
  },
  plugins: [],
}