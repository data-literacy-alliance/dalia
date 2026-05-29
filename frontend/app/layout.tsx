import type { Metadata } from 'next';
import './globals.css';
import './DALIAIcons.css';
import Footer from '@/app/_parts/Footer';
import { daliaFont, workSans } from '@/app/fonts';
import React from 'react';
// import CookieDialog from '@/app/_parts/CookieDialog';
import { config } from '@fortawesome/fontawesome-svg-core';
import '@fortawesome/fontawesome-svg-core/styles.css';
import NextTopLoader from 'nextjs-toploader';
import Providers from '@/app/Providers';
import AccessibilityDialog from '@/components/Accessibility';

config.autoAddCss = false;

export const metadata: Metadata = {
  title: 'DALIA',
  description: 'The best research data management app out there!',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${workSans.variable} ${daliaFont.variable}`} suppressHydrationWarning>
      <head>
        {/* Matomo Tag Manager — only injected when both env vars are set.
            Without the guard, missing vars produce a relative URL (js/container_.js)
            that causes a 404 on every page load in local dev.
            Set NEXT_PUBLIC_MATOMO_URL and NEXT_PUBLIC_MATOMO_CONTAINER_ID in production. */}
        {process.env.NEXT_PUBLIC_MATOMO_URL && process.env.NEXT_PUBLIC_MATOMO_CONTAINER_ID && (
          <script
            dangerouslySetInnerHTML={{
              __html: `
              var _mtm = window._mtm = window._mtm || [];
              _mtm.push({'mtm.startTime': (new Date().getTime()), 'event': 'mtm.Start'});
              (function() {
                var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
                g.async=true; g.src='${process.env.NEXT_PUBLIC_MATOMO_URL}js/container_${process.env.NEXT_PUBLIC_MATOMO_CONTAINER_ID}.js';
                s.parentNode.insertBefore(g,s);
              })();
            `,
            }}
          />
        )}
      </head>
      <body className={'font-dalia text-mobileText text-primary md:text-text'}>
        <NextTopLoader />
        <AccessibilityDialog />
        {/* <CookieDialog /> */}
        <Providers>{children}</Providers>
        <Footer />
      </body>
    </html>
  );
}
