'use client';

import React from 'react';
import { useAuth } from '@/context/auth-context';
import { redirect } from 'next/navigation';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { hasPrivilegedRole } from '@/lib/types';

type ProtectedRouteProps = {
  children: React.ReactNode;
  requirePrivilegedRole?: boolean;
};

export function ProtectedRoute({ children, requirePrivilegedRole = false }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
          <p className="text-slate-500 font-medium">인증 상태 확인 중...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    redirect('/login');
  }

  if (requirePrivilegedRole && !hasPrivilegedRole(user?.roles)) {
    return <AccessDeniedView reason="student-only" />;
  }

  return <>{children}</>;
}
