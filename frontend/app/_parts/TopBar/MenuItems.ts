import { ClassValue } from 'clsx';

type MenuItem = {
  path: string;
  label: string;
  disabled?: boolean;
  className?: ClassValue;
};

export const topMenuItems1: MenuItem[] = [
  {
    path: '/basic',
    label: 'Basic Search',
  },
  {
    path: '/advanced',
    label: 'Advanced Search',
  },
  // {
  //   path: '/explore',
  //   label: 'Explore',
  //   disabled: true,
  //   className: 'lg:hidden xl:flex',
  // },
];

export const topMenuItems2: MenuItem[] = [
  {
    path: '/communities',
    label: 'Communities',
    className: 'lg:hidden xl:flex',
  },
  {
    path: 'https://dalia.education/en#contact-section',
    label: 'Contact',
  },
];
