/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        graphite: '#0a0b0d',
        panel: '#12141a',
        'panel-raised': '#161922',
        teal: {
          400: '#2DD4BF',
          500: '#14b8a6',
          600: '#0d9488',
        },
        navy: '#1e3a5f',
        signal: {
          DEFAULT: '#f0a860',
          dim: '#f0a86040',
        },
        // Light theme surface tokens
        paper: '#fafaf8',
        'paper-raised': '#ffffff',
        ink: '#18181b',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      keyframes: {
        'trace-in': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-line': {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'trace-in': 'trace-in 0.4s ease-out forwards',
        'pulse-line': 'pulse-line 1.6s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
      },
    },
  },
  plugins: [],
}
