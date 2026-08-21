/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0F172A',
          secondary: '#1E293B',
          tertiary: '#334155',
        },
        accent: {
          blue: '#3B82F6',
          purple: '#8B5CF6',
          cyan: '#06B6D4',
        },
        risk: {
          critical: '#EF4444',
          high: '#F97316',
          medium: '#F59E0B',
          low: '#10B981',
          none: '#6B7280',
        },
        text: {
          primary: '#F1F5F9',
          secondary: '#94A3B8',
          muted: '#64748B',
        },
        border: {
          DEFAULT: '#334155',
          light: '#475569',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Noto Sans SC', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display': ['36px', { lineHeight: '1.2', fontWeight: '700' }],
        'h1': ['28px', { lineHeight: '1.2', fontWeight: '700' }],
        'h2': ['22px', { lineHeight: '1.2', fontWeight: '600' }],
        'h3': ['18px', { lineHeight: '1.3', fontWeight: '600' }],
        'body': ['14px', { lineHeight: '1.6' }],
        'caption': ['12px', { lineHeight: '1.5' }],
      },
      borderRadius: {
        'card': '12px',
        'btn': '8px',
        'input': '6px',
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 4px 16px rgba(59, 130, 246, 0.15)',
        'glow-blue': '0 0 12px rgba(59, 130, 246, 0.3)',
        'glow-red': '0 0 12px rgba(239, 68, 68, 0.3)',
      },
      animation: {
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.3s ease-out',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'count-up': 'count-up 0.8s ease-out',
        'shimmer': 'shimmer 1.5s ease-in-out infinite',
        'page-enter': 'page-enter 0.25s ease-out',
      },
      keyframes: {
        'pulse-dot': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.5', transform: 'scale(1.3)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'toast-shrink': {
          '0%': { width: '100%' },
          '100%': { width: '0%' },
        },
        'page-enter': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backgroundSize: {
        'shimmer': '200% 100%',
      },
    },
  },
  plugins: [],
}