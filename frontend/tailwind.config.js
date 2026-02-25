/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        'ms-dark': '#020617',    // Deep Background
        'ms-panel': '#0f172a',   // Panel Background
        'ms-emerald': '#10b981', // Accents / Safe status
        'ms-slate': '#94a3b8',   // Secondary / Watermark text
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}