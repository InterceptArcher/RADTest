/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Intercept red
        primary: {
          50: '#fef2f2',
          100: '#ffe1e0',
          200: '#ffc8c6',
          300: '#ffa09d',
          400: '#ff6b65',
          500: '#E02B23',
          600: '#c42520',
          700: '#a41e1a',
          800: '#881b17',
          900: '#731a18',
          950: '#3e0a08',
        },
        // Intercept neutrals
        slate: {
          850: '#1e1e1e',
          950: '#141414',
        },
        // Intercept accents
        accent: {
          blue: '#D1E1FD',
          blueDark: '#3b82f6',
          grey: '#939393',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'glow': '0 0 20px rgba(224, 43, 35, 0.1)',
        'glow-lg': '0 0 40px rgba(224, 43, 35, 0.15)',
        'inner-glow': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
        'card': '0 1px 2px rgba(0, 0, 0, 0.04), 0 1px 8px -1px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 1px 2px rgba(0, 0, 0, 0.04), 0 8px 24px -4px rgba(0, 0, 0, 0.1)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
