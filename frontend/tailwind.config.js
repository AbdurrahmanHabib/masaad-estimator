/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        'ms-primary': '#2C3E50',   // Deep Gunmetal (Material Strength)
        'ms-glass': '#0077B6',     // Ocean Blue (Glass Tint)
        'ms-accent': '#E67E22',    // Industrial Orange (Action)
        'ms-bg': '#F8F9FA',        // Architectural White (Cleanliness)
        'ms-dark': '#1A1A1A',      // Industrial Dark
      },
      fontFamily: {
        sans: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}