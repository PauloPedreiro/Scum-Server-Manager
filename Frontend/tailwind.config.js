/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    'bg-scum-dark',
    'bg-scum-primary',
    'bg-scum-secondary',
    'bg-scum-accent',
    'bg-scum-danger',
    'bg-scum-gray',
    'bg-scum-light',
    'bg-scum-muted',
    'text-scum-dark',
    'text-scum-primary',
    'text-scum-secondary',
    'text-scum-accent',
    'text-scum-danger',
    'text-scum-gray',
    'text-scum-light',
    'text-scum-muted',
    'border-scum-dark',
    'border-scum-primary',
    'border-scum-secondary',
    'border-scum-accent',
    'border-scum-danger',
    'border-scum-gray',
    'border-scum-light',
    'border-scum-muted',
  ],
  theme: {
    extend: {
      screens: {
        'xs': '475px',
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
      },
      colors: {
        // Tema SCUM - Cores militares e de sobrevivência
        scum: {
          primary: '#1a2e1a',      // Verde militar escuro
          secondary: '#6b8e23',     // Verde oliva
          accent: '#d2691e',        // Laranja enferrujado
          danger: '#8b0000',        // Vermelho sangue
          dark: '#0a0a0a',          // Preto profundo
          gray: '#2d2d2d',          // Cinza escuro
          light: '#f5f5dc',         // Branco sujo
          muted: '#d3d3d3',         // Cinza claro
        },
        military: {
          green: '#4a5d23',
          brown: '#8b4513',
          rust: '#cd5c5c',
          steel: '#696969',
        }
      },
      fontFamily: {
        military: ['Orbitron', 'monospace'],
        digital: ['Courier New', 'monospace'],
      },
      backgroundImage: {
        'scum-pattern': "url('data:image/svg+xml,%3Csvg width=\"60\" height=\"60\" viewBox=\"0 0 60 60\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cg fill=\"none\" fill-rule=\"evenodd\"%3E%3Cg fill=\"%231a2e1a\" fill-opacity=\"0.1\"%3E%3Cpath d=\"M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E')",
      },
      animation: {
        'glitch': 'glitch 0.3s infinite',
        'pulse-slow': 'pulse 3s infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
      },
      keyframes: {
        glitch: {
          '0%, 100%': { transform: 'translate(0)' },
          '20%': { transform: 'translate(-2px, 2px)' },
          '40%': { transform: 'translate(-2px, -2px)' },
          '60%': { transform: 'translate(2px, 2px)' },
          '80%': { transform: 'translate(2px, -2px)' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      },
      boxShadow: {
        'military': '0 4px 6px -1px rgba(26, 46, 26, 0.3), 0 2px 4px -1px rgba(26, 46, 26, 0.2)',
        'rust': '0 4px 6px -1px rgba(210, 105, 30, 0.3), 0 2px 4px -1px rgba(210, 105, 30, 0.2)',
      }
    },
  },
  plugins: [],
} 