import type { Config } from 'tailwindcss';
import defaultTheme from 'tailwindcss/defaultTheme';

const config: Config = {
  darkMode: ['class'],
  // list of plugins: https://tailwindcss.com/docs/configuration#core-plugins
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  safelist: [
    'text-h1',
    'text-h2',
    'text-h3',
    'text-h4',
    'text-subheader',
    'text-footerTitle',
    'text-footerTitle',
    'text-button',
    'text-footerText',
  ],
  theme: {
    extend: {
      fontFamily: {
        dalia: ['var(--work-sans)', ...defaultTheme.fontFamily.sans],
      },
      fontSize: (utils) => ({
        h1: [
          '4rem',
          {
            fontWeight: utils.theme('fontWeight.semibold') as string,
          },
        ],
        h2: [
          '3rem',
          {
            fontWeight: utils.theme('fontWeight.semibold') as string,
          },
        ],
        h3: [
          '2.25rem',
          {
            fontWeight: utils.theme('fontWeight.semibold') as string,
          },
        ],
        h4: [
          '2rem',
          {
            fontWeight: utils.theme('fontWeight.semibold') as string,
          },
        ],
        subheader: [
          '1.25rem',
          {
            fontWeight: utils.theme('fontWeight.normal') as string,
          },
        ],
        footerTitle: [
          '1.125rem',
          {
            fontWeight: utils.theme('fontWeight.semibold') as string,
          },
        ],
        button: [
          '1.25rem',
          {
            fontWeight: utils.theme('fontWeight.normal') as string,
          },
        ],
        text: [
          '1rem',
          {
            fontWeight: utils.theme('fontWeight.normal') as string,
          },
        ],
        mobileText: [
          '1rem',
          {
            fontWeight: utils.theme('fontWeight.normal') as string,
          },
        ],
        footerText: [
          '1rem',
          {
            fontWeight: utils.theme('fontWeight.normal') as string,
          },
        ],
      }),
      colors: {
        primary: '#000050',
        accent: '#00F7F7',
        dalia1: '#00CFC3',
        dalia2: '#9747FF',
        dalia3: '#FF42E1',
        dalia4: '#FF005C',
        dalia5: '#FF7B42',
        daliaBlue: {
          '100': '#0000E0',
          '200': '#0000BA',
          '300': '#000094',
          '400': '#00006E',
        },
        daliaGray: {
          '100': '#F3F3F3',
          '200': '#D3D3D3',
          '300': '#8F8F8F',
          A6: 'rgba(211, 211, 211, 0.75)',
        },
      },
      keyframes: {
        no: {
          '0%, 50%, 100%': {
            transform: 'translateX(-5px)',
          },
          '25%, 75%': {
            transform: 'translateX(5px)',
          },
        },
        slideDownAndFade: {
          from: {
            opacity: '0',
            transform: 'translateY(-2px)',
          },
          to: {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        slideLeftAndFade: {
          from: {
            opacity: '0',
            transform: 'translateX(2px)',
          },
          to: {
            opacity: '1',
            transform: 'translateX(0)',
          },
        },
        slideUpAndFade: {
          from: {
            opacity: '0',
            transform: 'translateY(2px)',
          },
          to: {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        slideRightAndFade: {
          from: {
            opacity: '0',
            transform: 'translateX(-2px)',
          },
          to: {
            opacity: '1',
            transform: 'translateX(0)',
          },
        },
        slideDown: {
          from: {
            height: '0',
          },
          to: {
            height: 'var(--radix-accordion-content-height)',
          },
        },
        slideUp: {
          from: {
            height: 'var(--radix-accordion-content-height)',
          },
          to: {
            height: '0',
          },
        },
        'accordion-down': {
          from: {
            height: '0',
          },
          to: {
            height: 'var(--radix-accordion-content-height)',
          },
        },
        'accordion-up': {
          from: {
            height: 'var(--radix-accordion-content-height)',
          },
          to: {
            height: '0',
          },
        },
      },
      animation: {
        no: 'no 0.5s ease-in-out',
        slideDownAndFade:
          'slideDownAndFade 400ms cubic-bezier(0.16, 1, 0.3, 1)',
        slideLeftAndFade:
          'slideLeftAndFade 400ms cubic-bezier(0.16, 1, 0.3, 1)',
        slideUpAndFade: 'slideUpAndFade 400ms cubic-bezier(0.16, 1, 0.3, 1)',
        slideRightAndFade:
          'slideRightAndFade 400ms cubic-bezier(0.16, 1, 0.3, 1)',
        slideDown: 'slideDown 300ms cubic-bezier(0.87, 0, 0.13, 1)',
        slideUp: 'slideUp 300ms cubic-bezier(0.87, 0, 0.13, 1)',
        overlayShow: 'overlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',
        contentShow: 'contentShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};

export default config;
