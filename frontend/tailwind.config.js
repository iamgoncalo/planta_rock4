/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        critical: '#C25A1A',
        success: '#1B3A21',
        accent: '#4A7C59',
        surface: '#FAFAF7',
        ink: '#1A1A1A',
        muted: '#6B7280',
        border: '#DEE8DE',
      },
      fontFamily: {
        display: ['Cormorant Garamond', 'Georgia', 'serif'],
        ui: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
      fontSize: {
        'kpi': ['56px', { lineHeight: '1', fontWeight: '400' }],
        'tv-main': ['84px', { lineHeight: '1', fontWeight: '700' }],
        'app-hero': ['48px', { lineHeight: '1.1', fontWeight: '700' }],
        'app-sub': ['36px', { lineHeight: '1.2', fontWeight: '500' }],
      },
    },
  },
  plugins: [],
};
