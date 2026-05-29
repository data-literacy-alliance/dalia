'use client';
import React, { useEffect, useState } from 'react';
import { clientLogout, useAuthLogin } from '@/lib/auth/clientAuth';

export default function LogoutPage() {
  const [failed, setFailed] = useState(false);
  const { access } = useAuthLogin();

  useEffect(() => {
    if (access) {
      clientLogout(access)
        .then((result) => {
          if (result) {
            window.location.href = '/';
          } else {
            setFailed(true);
          }
        })
        .catch(() => {
          setFailed(true);
        });
    }
  }, [access]);

  return <div>{failed ? 'Failed to logout!.' : 'Logging out...'}</div>;
}
