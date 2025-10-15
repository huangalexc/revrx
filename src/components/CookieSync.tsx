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
  useEffect(() => {
    // On mount, restore cookie from localStorage if needed
    const storedToken = localStorage.getItem('auth_token');

    if (storedToken) {
      // Check if cookie exists
      const hasCookie = document.cookie.split(';').some(
        (item) => item.trim().startsWith('auth_token=')
      );

      // If no cookie but we have localStorage token, restore it
      if (!hasCookie) {
        document.cookie = `auth_token=${storedToken}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax; Secure=${process.env.NODE_ENV === 'production'}`;
      }
    }
  }, []); // Run only once on mount

  return null; // This component doesn't render anything
}
