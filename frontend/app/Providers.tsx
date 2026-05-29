'use client';
import React, { Dispatch, FC, useContext, useState } from 'react';
import { usePathname } from 'next/navigation';

type MainContextType = {
  sidebarOpen: boolean;
  setSidebarOpen: Dispatch<React.SetStateAction<boolean>>;
};

const MainContext = React.createContext<MainContextType | null>(null);

export function useMainContext() {
  const context = useContext(MainContext);
  if (!context) {
    throw new Error('useMainContext should be used inside Providers tag.');
  }
  return context;
}

const Providers: FC<ProvidersProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [lastPathname, setLastPathname] = useState('');
  const pathname = usePathname();

  if (pathname !== lastPathname) {
    setSidebarOpen(false); // reset sidebar on page change
    setLastPathname(pathname);
  }

  return (
    <MainContext.Provider value={{ sidebarOpen, setSidebarOpen }}>
      {children}
    </MainContext.Provider>
  );
};

export type ProvidersProps = {
  children: React.ReactNode;
};

export default Providers;
