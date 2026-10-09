import { Dispatch, SetStateAction, useCallback, useRef, useState } from 'react';

export function useDebouncedState<T>(delay: number, init: T | (() => T)) {
  const [liveValue, setLiveLiveValue] = useState(init);
  const [debouncedValue, setDebouncedValue] = useState(init);
  const timer = useRef<NodeJS.Timeout | undefined>();

  const setValue: Dispatch<SetStateAction<T>> =
    useCallback((newValue) => {
      setLiveLiveValue(newValue);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        setDebouncedValue(newValue);
      }, delay)
    }, [delay]);

  return {
    debouncedValue,
    liveValue: liveValue,
    setValue,
  }
}
