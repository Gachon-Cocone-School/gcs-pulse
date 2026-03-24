'use client';

import React from 'react';
import { Navigation } from '../Navigation';
import { Button } from '@/components/ui/button';
import { ShieldAlert, LogOut } from 'lucide-react';
import { useAuth } from '@/context/auth-context';

type AccessDeniedReason = 'student-only' | 'no-role';

type AccessDeniedViewProps = {
  reason?: AccessDeniedReason;
};

export function AccessDeniedView({ reason = 'no-role' }: AccessDeniedViewProps) {
  const { logout } = useAuth();
  const [clientHostId, setClientHostId] = React.useState('');

  React.useEffect(() => {
    setClientHostId(btoa(window.location.host).slice(0, 8));
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navigation />

      <main className="max-w-7xl mx-auto px-6 py-16 flex flex-col items-center">
        <div className="w-20 h-20 bg-destructive/10 rounded-full flex items-center justify-center mb-6">
          <ShieldAlert className="w-10 h-10 text-destructive" />
        </div>

        <h1 className="text-3xl font-bold text-foreground mb-4 text-center">접근 권한이 없습니다</h1>
        <p className="text-muted-foreground text-lg mb-8 text-center max-w-lg">
          {reason === 'student-only'
            ? 'GCS 학생만 이용할 수 있습니다.'
            : '정상적으로 로그인되었으나, 서비스를 이용할 수 있는 권한이 부여되지 않았습니다. 관리자에게 수강 승인을 요청하거나 고객센터에 문의해 주세요.'}
        </p>

        <div className="w-full max-w-sm">
          <Button
            type="button"
            variant="outline"
            onClick={() => logout()}
            className="h-auto w-full flex-col items-center p-[19px] text-center border-primary/40 hover:border-primary hover:bg-primary/5 transition-colors group hover:shadow-md"
          >
            <LogOut className="w-6 h-6 text-primary mb-2 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-foreground mb-1">로그아웃</h3>
            <p className="text-sm text-muted-foreground">다른 계정으로 로그인</p>
          </Button>
        </div>

        <div className="mt-12 text-muted-foreground text-sm">ID: {clientHostId}</div>
      </main>
    </div>
  );
}
