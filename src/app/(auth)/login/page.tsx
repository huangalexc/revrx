'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import apiClient from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import { useAuthStore } from '@/store/authStore';

export default function LoginPage() {
  const router = useRouter();
  const { setUser, setToken } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await apiClient.post(API_ENDPOINTS.AUTH.LOGIN, {
        email,
        password,
      });

      const { user, tokens } = response.data;
      console.log('Login successful, full response:', response.data);
      console.log('Tokens object:', tokens);
      console.log('Tokens keys:', Object.keys(tokens));
      console.log('Access token (accessToken):', tokens.accessToken);
      console.log('Access token (access_token):', tokens.access_token);
      console.log('Token type:', typeof tokens.accessToken);
      console.log('Token length:', tokens.accessToken?.length);

      // Test localStorage is working
      console.log('localStorage available:', typeof localStorage !== 'undefined');
      localStorage.setItem('test_key', 'test_value');
      console.log('Test key saved:', localStorage.getItem('test_key'));

      // Manually save to localStorage FIRST
      const saveResult = localStorage.setItem('auth_token', tokens.accessToken);
      console.log('setItem returned:', saveResult);
      console.log('Token manually saved to localStorage');

      // Check immediately
      const checkToken1 = localStorage.getItem('auth_token');
      console.log('Immediate check - token exists:', !!checkToken1);
      console.log('Immediate check - token value:', checkToken1?.substring(0, 20));

      setUser(user);
      setToken(tokens.accessToken);

      // Verify it was saved after zustand
      const savedToken = localStorage.getItem('auth_token');
      console.log('After zustand - Token saved to localStorage:', !!savedToken);
      console.log('After zustand - Saved token matches:', savedToken === tokens.accessToken);
      console.log('After zustand - All keys:', Object.keys(localStorage));

      // Set cookie for middleware (max-age in seconds, default to 7 days)
      const maxAge = tokens.expiresIn || 604800; // 7 days in seconds
      document.cookie = `auth_token=${tokens.accessToken}; path=/; max-age=${maxAge}; SameSite=Lax`;
      console.log('Cookie set with max-age:', maxAge);

      router.push('/encounters/new');
    } catch (err: any) {
      setError(
        err.response?.data?.detail || err.response?.data?.message || 'Invalid email or password'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to RevRx
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Post-Facto Coding Review Platform
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Password"
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="text-sm">
              <Link
                href="/register"
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                Create an account
              </Link>
            </div>
            <div className="text-sm">
              <Link
                href="/forgot-password"
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                Forgot password?
              </Link>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
