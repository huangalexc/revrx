'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';

/**
 * CookieSync Component
 *
 * Ensures the auth cookie is synced with localStorage on page load.
 * This fixes the issue where page refresh logs the user out because
 * the middleware checks for the cookie (server-side) but Zustand
 * rehydrates from localStorage (client-side).
 */
export function CookieSync() {
  const token = useAuthStore((state) => state.token);

  useEffect(() => {
    // On mount, check if we have a token in localStorage but not in cookie
    const storedToken = localStorage.getItem('auth_token');

    if (storedToken) {
      // Check if cookie exists
      const hasCookie = document.cookie.split(';').some(
        (item) => item.trim().startsWith('auth_token=')
      );

      // If no cookie but we have localStorage token, restore the cookie
      if (!hasCookie) {
        const maxAge = 604800; // 7 days in seconds
        document.cookie = `auth_token=${storedToken}; path=/; max-age=${maxAge}; SameSite=Lax`;
        console.log('[CookieSync] Restored auth cookie from localStorage');
      }
    }
  }, [token]);

  return null; // This component doesn't render anything
}
