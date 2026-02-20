'use client';

import React, { useEffect, useState } from 'react';
import { redirect, useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import LoginPageClient from './login/LoginPageClient';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Navigation } from '@/components/Navigation';

interface Term {
  id: number;
  is_required: boolean;
}

export default function HomePageClient() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [checkingConsents, setCheckingConsents] = useState(true);
  const [mustAgreeTerms, setMustAgreeTerms] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const verifyConsents = async () => {
      try {
        if (isAuthenticated && user) {
          // Fetch all terms to see which ones are required
          const terms = await api.get<Term[]>('/terms');
          const requiredTermIds = terms.filter(t => t.is_required).map(t => t.id);

          // Check if user has agreed to all required terms
          const agreedTermIds = user.consents.map(c => c.term_id);
          const allAgreed = requiredTermIds.every(id => agreedTermIds.includes(id));

          setMustAgreeTerms(!allAgreed);
        }
      } catch (error) {
        console.error('Failed to verify consents:', error);
      } finally {
        setCheckingConsents(false);
      }
    };

    if (!isLoading) {
      verifyConsents();
    }
  }, [isAuthenticated, user, isLoading, router]);

  // 1. 로딩 중
  if (isLoading || (isAuthenticated && checkingConsents)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-rose-500 animate-spin" />
          <p className="text-slate-500 font-medium">유저 정보를 확인 중입니다...</p>
        </div>
      </div>
    );
  }

  // 2. 미인증 사용자 -> 로그인 페이지 표시
  if (!isAuthenticated) {
    return <LoginPageClient />;
  }

  // 3. 약관 동의 필요 사용자
  if (mustAgreeTerms) {
    redirect('/terms');
  }

  // 4. 권한 체크 -> 역할이 없는 경우 접근 불가 표시
  // (프로젝트 설정에 따라 role 체크 로직은 변경 가능합니다)
  const hasAccess = user?.roles && user.roles.length > 0;

  if (!hasAccess) {
    return <AccessDeniedView />;
  }

  // 5. 모든 조건 통과 -> 메인 대시보드 표시 (Minimal Hero)
  return (
    <div className="min-h-screen bg-slate-50 bg-mesh">
      <Navigation />
      <main className="flex flex-col items-center justify-center p-4 md:py-10">
        <div className="w-full max-w-5xl space-y-8 animate-entrance">
          <div className="text-center space-y-4 glass-card p-8 md:p-10 rounded-xl">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900">
              <span className="premium-gradient-text">GCS Snippets</span>
            </h1>
            <p className="text-xl text-slate-600 leading-relaxed">
              작은 기록이 모여
              <span className="font-semibold text-slate-800"> 특별한 성장</span>을 만듭니다.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass-card p-8 md:p-10 rounded-xl text-center space-y-6">
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">일간 스니펫</h2>
              <p className="text-slate-600 leading-relaxed">하루를 정리하며 꾸준한 성장을 기록해보세요.</p>
              <Button
                size="lg"
                className="w-full text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all rounded-full bg-rose-500 hover:bg-rose-600 text-white"
                onClick={() => router.push('/daily-snippets')}
              >
                일간 스니펫
              </Button>
            </div>

            <div className="glass-card p-8 md:p-10 rounded-xl text-center space-y-6">
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">주간 스니펫</h2>
              <p className="text-slate-600 leading-relaxed">한 주를 돌아보며 핵심 인사이트를 남겨보세요.</p>
              <Button
                size="lg"
                className="w-full text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all rounded-full bg-rose-500 hover:bg-rose-600 text-white"
                onClick={() => router.push('/weekly-snippets')}
              >
                주간 스니펫
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
