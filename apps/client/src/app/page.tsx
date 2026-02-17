'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import LoginPage from './login/page';
import { AccessDeniedView } from '@/components/views/AccessDenied';

interface Term {
  id: number;
  is_required: boolean;
}

export default function Home() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [checkingConsents, setCheckingConsents] = useState(true);
  const [mustAgreeTerms, setMustAgreeTerms] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const verifyConsents = async () => {
      if (isAuthenticated && user) {
        try {
          // Fetch all terms to see which ones are required
          const terms = await api.get<Term[]>('/terms');
          const requiredTermIds = terms.filter(t => t.is_required).map(t => t.id);

          // Check if user has agreed to all required terms
          const agreedTermIds = user.consents.map(c => c.term_id);
          const allAgreed = requiredTermIds.every(id => agreedTermIds.includes(id));

          if (!allAgreed) {
            setMustAgreeTerms(true);
            router.push('/terms');
          }
        } catch (error) {
          console.error('Failed to verify consents:', error);
        } finally {
          setCheckingConsents(false);
        }
      } else {
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
    return <LoginPage />;
  }

  // 3. 약관 동의 필요 사용자 (useEffect에서 push하므로 여기서는 빈 화면 또는 로딩 표시)
  if (mustAgreeTerms) {
    return null;
  }

  // 4. 권한 체크 -> 역할이 없는 경우 접근 불가 표시
  // (프로젝트 설정에 따라 role 체크 로직은 변경 가능합니다)
  const hasAccess = user?.roles && user.roles.length > 0;

  if (!hasAccess) {
    return <AccessDeniedView />;
  }

  // 5. 모든 조건 통과 -> 메인 대시보드 표시 (Minimal Hero)
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-slate-50 bg-mesh">
      <div className="max-w-2xl text-center space-y-8 glass-card p-12 rounded-xl animate-entrance">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900">
          <span className="premium-gradient-text">Daily Snippets</span>
        </h1>
        <p className="text-xl text-slate-600 leading-relaxed">
          매일의 작은 기록이 모여<br />
          <span className="font-semibold text-slate-800">특별한 성장</span>을 만듭니다.
        </p>

        <div className="flex flex-col sm:flex-row justify-center items-stretch sm:items-center gap-3 pt-4">
          <Button
            size="lg"
            className="w-full sm:w-auto text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all rounded-full bg-rose-500 hover:bg-rose-600 text-white"
            onClick={() => router.push('/daily-snippets')}
          >
            일간 스니펫 작성하기
          </Button>
          <Button
            size="lg"
            className="w-full sm:w-auto text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all rounded-full bg-rose-500 hover:bg-rose-600 text-white"
            onClick={() => router.push('/weekly-snippets')}
          >
            주간 스니펫 작성하기
          </Button>
        </div>
      </div>
    </main>
  );
}
