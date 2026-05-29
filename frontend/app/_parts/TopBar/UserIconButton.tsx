'use client';
import React from 'react';
import IconButton from '@/components/IconButton';
import Button from '@/components/Button';
import { Loader2Icon } from 'lucide-react';
import { LoginURL } from '@/lib/settings.mjs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useUserInfo } from '@/lib/auth/authApi';
import Cookies from 'js-cookie';
import { AUTH_ACCESS_KEY, AUTH_REFRESH_KEY } from '@/lib/auth/authSettings';

const UserIconButton = () => {
  const { userInfo: loggedIn, isLoading } = useUserInfo();

  const handleLogout = () => {
    // Clear JWT cookies (if present — JWT/OIDC users).
    // Django/allauth session termination is handled by the full-page navigation below,
    // which works for both session-only users (admin/two_factor) and JWT/OIDC users.
    Cookies.remove(AUTH_ACCESS_KEY);
    Cookies.remove(AUTH_REFRESH_KEY);
    // Full-page navigation so allauth's CSRF-protected logout form runs correctly.
    // Never use Next.js Link/router for this URL — it would send an RSC request to Django.
    window.location.href = '/accounts/logout/';
  };

  return isLoading ? (
    <Loader2Icon className={'mx-2 animate-spin'} />
  ) : (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconButton source={'user'} borderless dark />
      </DropdownMenuTrigger>
      <DropdownMenuPortal>
        <DropdownMenuContent align={'end'}>
          {loggedIn ? (
            <>
              <DropdownMenuItem asChild>
                <Button
                  className={'w-full'}
                  borderless
                  link={{
                    href: '/profile/',
                  }}
                >
                  Profile
                </Button>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Button
                  className={'w-full'}
                  borderless
                  onClick={handleLogout}
                >
                  Logout
                </Button>
              </DropdownMenuItem>
            </>
          ) : (
            <>
              <DropdownMenuItem asChild>
                <Button
                  className={'w-full'}
                  dark
                  borderless
                  link={{ href: LoginURL }}
                >
                  Login
                </Button>
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </DropdownMenu>
  );
};

export default UserIconButton;
