'use client';

import { redirect } from 'next/navigation';

import { Navigation } from '@/components/Navigation';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { useAuth } from '@/context/auth-context';
import { hasPrivilegedRole } from '@/lib/types';

export default function ProfessorPageClient() {
  const { user, isAuthenticated, isLoading } = useAuth();

  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">교수 멘토링 화면을 준비 중입니다...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    redirect('/login');
  }

  if (!hasAccess || !isProfessor) {
    return <AccessDeniedView reason="student-only" />;
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <section className="rounded-xl border border-border bg-card/80 p-8">
          <h1 className="text-xl font-semibold text-foreground">교수 멘토링</h1>
          <p className="mt-2 text-sm text-muted-foreground">준비 중인 페이지입니다.</p>
        </section>
      </main>
    </div>
  );
}
