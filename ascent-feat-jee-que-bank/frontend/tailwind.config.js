import colors from 'tailwindcss/colors';

/* Dark theme for the whole app: every palette is inverted (50 <-> 950, 100 <-> 900, ...), so the
   existing "bg-white text-slate-900 border-slate-200" components render on dark surfaces unchanged. */
const invert = (scale) => Object.fromEntries(Object.entries(scale).map(([k, v]) => [k, scale[String(1000 - Number(k))] ?? v]));
const inverted = Object.fromEntries(
  ['gray', 'zinc', 'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal', 'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose']
    .map((n) => [n, invert(colors[n])]),
);

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      boxShadow: {
        '2xs': '0 1px rgb(15 23 42 / 0.04)',
        xs: '0 1px 2px 0 rgb(15 23 42 / 0.06)',
      },
      backgroundColor: {
        white: '#11141e',          // card / sidebar surface
      },
      colors: {
        ...inverted,
        // slate, inverted by hand: page bg -> borders -> muted text -> headings
        slate: {
          50: '#0b0d14', 100: '#11141e', 200: '#1e2332', 300: '#2b3144', 400: '#6b7389', 500: '#8f97ab',
          600: '#aeb5c6', 700: '#cdd2de', 800: '#e3e6ee', 900: '#f3f5f9', 950: '#ffffff',
        },
        // Variant Studio dark palette
        ink: {
          950: '#07080d', 900: '#0d0f17', 850: '#11141e', 800: '#161a26', 750: '#1c2130',
          700: '#252b3c', 600: '#343b50', 500: '#5b6379', 400: '#8a92a8', 300: '#b4bacb', 200: '#d6dae4', 100: '#eef0f6',
        },
        iris: { 300: '#c9b8ff', 400: '#a88bff', 500: '#8257ff', 600: '#7038ff', 700: '#5f26e6' },
        brand: {
          50: '#f4f1ff',
          100: '#ebe5ff',
          200: '#d8ccff',
          300: '#bba5ff',
          400: '#9d7bff',
          500: '#8257ff',
          600: '#7038ff',
          700: '#5f26e6',
          800: '#4d1fbb',
          900: '#3f1c93',
          950: '#250e5e',
        },
        neon: { cyan: '#22e4ff', blue: '#4d7cff', violet: '#8257ff', pink: '#ff3ec9', lime: '#7dffb2', amber: '#ffd166' },
      },
    },
  },
  plugins: [],
}

