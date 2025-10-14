'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export default function ProtectedRoute({
  children,
  requireAdmin = false,
}: ProtectedRouteProps) {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (requireAdmin && user?.role !== 'ADMIN') {
      router.push('/summary');
    }
  }, [isAuthenticated, user, requireAdmin, router]);

  if (!isAuthenticated) {
    return null;
  }

  if (requireAdmin && user?.role !== 'ADMIN') {
    return null;
  }

  return <>{children}</>;
}
