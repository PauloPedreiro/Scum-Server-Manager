/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    screens: {
      xs: '480px',
      sm: '640px',
      md: '768px',
      lg: '992px',
      xl: '1200px',
      '2xl': '1536px',
    },
    extend: {
      colors: {
        scum: {
          bg: '#0b0e13',
          panel: '#121721',
          accent: '#f97316',
          orange: '#f97316',
          'orange-hover': '#ea580c',
        },
      },
    },
  },
  darkMode: 'class',
  plugins: [],
};


