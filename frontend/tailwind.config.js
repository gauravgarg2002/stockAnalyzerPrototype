/** @type {import('tailwindcss').Config} */

// Plainfolio theme: "see-through". Solid peacock-ink surfaces, one marigold accent, lagoon for "through funds".
// The existing `slate` and `indigo` utility names are remapped to the theme scales, so every screen picks it up.
// Deliberately no red or green anywhere: colour never signals a verdict.
const ink = {
  50: '#F4F7F6',
  100: '#E7EEEC',
  200: '#D4DFDC',
  300: '#B6C6C2',
  400: '#8A9E9A',
  500: '#647D7A',
  600: '#4A6265',
  700: '#33494F',
  800: '#22363D',
  900: '#15252C',
  950: '#0B171C',
};

const peacock = {
  50: '#E8F4F5',
  100: '#CCE8EA',
  200: '#9FD3D6',
  300: '#6CB7BE',
  400: '#3B97A2',
  500: '#1C7F8C',
  600: '#136E7C',
  700: '#0F5E6C',
  800: '#0B4A57',
  900: '#0B3B4F',
  950: '#072833',
};

const marigold = {
  50: '#FEF6E7',
  100: '#FDEAC4',
  200: '#FAD58A',
  300: '#F8C35D',
  400: '#F4A92B',
  500: '#E08E12',
  600: '#B86F06',
  700: '#8C5408',
};

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        slate: ink,
        indigo: peacock,
        ink,
        peacock,
        marigold,
        lagoon: { 100: '#DDF0F1', 200: '#BFE3E5', 300: '#9FD3D6', 400: '#7CC0C5' },
        stone: { 50: '#F2F4EF', 100: '#E9ECE5', 200: '#D9CDB0', 300: '#C6B48A' },
        paper: '#F2F4EF',
      },
      fontFamily: {
        sans: ['"Hanken Grotesk"', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Arial', 'sans-serif'],
        display: ['"Bricolage Grotesque"', '"Hanken Grotesk"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      maxWidth: { page: '74rem' },
      borderRadius: { sheet: '1.375rem' },
      boxShadow: {
        // A crisp "stacked sheet" edge instead of a soft grey blur.
        sheet: '0 1px 0 rgba(11, 59, 79, 0.06), 0 6px 0 -3px rgba(11, 59, 79, 0.07)',
        lift: '0 2px 0 rgba(11, 59, 79, 0.08), 0 18px 40px -18px rgba(11, 59, 79, 0.35)',
        lens: '0 0 0 1px rgba(244, 169, 43, 0.5), 0 10px 30px -10px rgba(244, 169, 43, 0.45)',
      },
      keyframes: {
        rise: { from: { opacity: '0', transform: 'translateY(14px)' }, to: { opacity: '1', transform: 'none' } },
        fade: { from: { opacity: '0' }, to: { opacity: '1' } },
        pop: { '0%': { opacity: '0', transform: 'scale(.96)' }, '100%': { opacity: '1', transform: 'none' } },
        shimmer: { from: { backgroundPosition: '-480px 0' }, to: { backgroundPosition: '480px 0' } },
        'slide-in-right': { from: { transform: 'translateX(100%)' }, to: { transform: 'none' } },
        'slide-in-up': { from: { transform: 'translateY(100%)' }, to: { transform: 'none' } },
        'grow-x': { from: { transform: 'scaleX(0)' }, to: { transform: 'scaleX(1)' } },
        drift: { '0%,100%': { transform: 'translate3d(0,0,0)' }, '50%': { transform: 'translate3d(0,-6px,0)' } },
        ping: { '75%,100%': { transform: 'scale(2.2)', opacity: '0' } },
      },
      animation: {
        rise: 'rise .6s cubic-bezier(.2,.7,.2,1) both',
        fade: 'fade .35s ease-out both',
        pop: 'pop .18s cubic-bezier(.2,.7,.2,1) both',
        shimmer: 'shimmer 1.4s linear infinite',
        'slide-in-right': 'slide-in-right .32s cubic-bezier(.2,.7,.2,1) both',
        'slide-in-up': 'slide-in-up .32s cubic-bezier(.2,.7,.2,1) both',
        'grow-x': 'grow-x .9s cubic-bezier(.2,.7,.2,1) both',
        drift: 'drift 6s ease-in-out infinite',
        ping: 'ping 1.6s cubic-bezier(0,0,.2,1) infinite',
      },
    },
  },
  plugins: [],
};
