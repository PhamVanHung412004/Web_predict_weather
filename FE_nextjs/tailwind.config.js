/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        accent: '#06b6d4',
        accent2: '#8b5cf6',
        card: 'rgba(255,255,255,0.03)'
      }
    }
  },
  plugins: [require('@tailwindcss/forms')],
}
