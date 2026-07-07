/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: '#00352e',
          primaryHover: '#004a3f',
          secondary: '#904d00',
          surface: '#f9faf7',
          border: '#e3e8e6',
          danger: '#b91c1c',
          success: '#166534',
        },
        text: {
          primary: '#111a18',
          secondary: '#4a6360',
        }
      },
      fontFamily: {
        sans: ['"Hanken Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        sm: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
      borderRadius: {
        'lg': '12px',
        'md': '8px',
        'xl': '16px',
        '2xl': '20px',
        'pill': '20px',
      }
    },
  },
  plugins: [],
}
