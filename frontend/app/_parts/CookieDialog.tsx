'use client';
import React, { FC, useCallback, useEffect, useRef, useState } from 'react';
import Button from '@/components/Button';
import Cookies from 'js-cookie';
import { GDPRCookieName } from '@/lib/settings.mjs';
import * as Dialog from '@radix-ui/react-dialog';
import Link from 'next/link';

const CookieDialog: FC<{}> = () => {
  const [open, setOpen] = useState(false);
  const firstTime = useRef(true);

  const handleNewOpen = useCallback((newOpen: boolean) => {
    if (!newOpen) {
      Cookies.set(GDPRCookieName, '1', {
        sameSite: 'Lax',
        expires: new Date(new Date().setFullYear(new Date().getFullYear() + 1)),
      });
    } else {
      Cookies.remove(GDPRCookieName, { sameSite: 'Lax' });
    }
    setOpen(newOpen);
  }, []);

  useEffect(() => {
    if (window && firstTime.current) {
      firstTime.current = false;
      setOpen(!Cookies.get(GDPRCookieName));
    }
  }, []);

  return (
    <Dialog.Root open={open} onOpenChange={handleNewOpen} modal={false}>
      <Dialog.Portal>
        <Dialog.Content
          className="fixed bottom-0 max-h-[85vh] rounded-t-[6px] bg-white p-5 shadow-[hsl(206_22%_7%_/_35%)_0px_10px_38px_-10px,_hsl(206_22%_7%_/_20%)_0px_10px_20px_-15px] focus:outline-none data-[state=open]:animate-contentShow lg:left-[50%] lg:translate-x-[-50%]"
          onEscapeKeyDown={(e) => {
            e.preventDefault();
          }}
          onPointerDownOutside={(e) => {
            e.preventDefault();
          }}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <Dialog.Title className="text-mauve12 m-0 text-[1.06rem] font-medium">
            Cookie Policy
          </Dialog.Title>
          <Dialog.Description className="mb-5 mt-4 text-[0.9375rem] leading-normal text-primary">
            <span className={'flex flex-col md:flex-row'}>
              <span className={'flex-1'}>
                We do not use cookies that store personal data and do not use
                any tracking methods. Only technically necessary cookies are
                used for the operation of the website. For more information,
                please see our{' '}
                <Link
                  href="/en/privacy-policy"
                  className="underline hover:text-primary-dark"
                  target="_blank"
                >
                  Privacy Policy
                </Link>
                .
              </span>
              <Dialog.Close asChild>
                <Button small>Understood</Button>
              </Dialog.Close>
            </span>
          </Dialog.Description>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default CookieDialog;
