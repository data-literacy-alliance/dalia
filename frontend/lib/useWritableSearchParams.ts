'use client';

import { useSearchParams } from 'next/navigation';
import { useMemo } from 'react';

export default function useWritableSearchParams() {
  const params = useSearchParams();

  return useMemo(() => {
    return new URLSearchParams(params);
  }, [params]);
}
