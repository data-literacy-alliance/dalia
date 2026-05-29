'use client';
import { RefObject, useCallback, useEffect } from 'react';

export default function useTypingSearch(input: RefObject<HTMLInputElement>) {
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInputElement =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable;

      if (
        input.current &&
        e.target !== input.current &&
        e.key.length === 1 &&
        !isInputElement
      ) {
        input.current.focus();
      }
    },
    [input]
  );

  useEffect(() => {
    if (!document) {
      return;
    }

    document.addEventListener('keydown', handleKey);

    return () => {
      document.removeEventListener('keydown', handleKey);
    };
  }, [handleKey]);
}
