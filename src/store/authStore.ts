import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  role: 'ADMIN' | 'USER';
  trialEndDate?: string;
  subscriptionStatus?: 'active' | 'trialing' | 'canceled' | 'expired';
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => {
        if (typeof window !== 'undefined') {
          if (token) {
            localStorage.setItem('auth_token', token);
            // Also set cookie for middleware (7 days)
            const maxAge = 604800; // 7 days in seconds
            document.cookie = `auth_token=${token}; path=/; max-age=${maxAge}; SameSite=Lax`;
          } else {
            localStorage.removeItem('auth_token');
            document.cookie = 'auth_token=; path=/; max-age=0';
          }
        }
        set({ token });
      },
      logout: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
          // Clear the cookie by setting max-age to 0
          document.cookie = 'auth_token=; path=/; max-age=0';
        }
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? localStorage : {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        }
      ),
    }
  )
);
