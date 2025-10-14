'use client';

import { HeroUIProvider } from '@heroui/react';
import ThemeProvider from './ThemeProvider';
import { CookieSync } from './CookieSync';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <HeroUIProvider>
      <ThemeProvider>
        <CookieSync />
        {children}
      </ThemeProvider>
    </HeroUIProvider>
  );
}
