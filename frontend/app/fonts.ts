import { Work_Sans } from 'next/font/google';
import localFont from 'next/font/local';

export const workSans = Work_Sans({
  subsets: ['latin', 'latin-ext', 'vietnamese'],
  variable: '--work-sans',
  display: 'swap',
});

export const daliaFont = localFont({
  src: './DALIAIcons.ttf',
  variable: '--dalia-font',
  display: 'swap',
});
