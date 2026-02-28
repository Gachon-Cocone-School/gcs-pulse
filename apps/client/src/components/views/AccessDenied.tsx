'use client';

import React from 'react';
import { Navigation } from '../Navigation';
import { Card } from '@/components/ui/card';
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
    <div className="min-h-screen bg-slate-50">
      <Navigation />

      <main className="max-w-7xl mx-auto px-6 py-16 flex flex-col items-center">
        <div className="w-20 h-20 bg-rose-100 rounded-full flex items-center justify-center mb-6">
          <ShieldAlert className="w-10 h-10 text-rose-600" />
        </div>

        <h1 className="text-3xl font-bold text-slate-900 mb-4 text-center">접근 권한이 없습니다</h1>
        <p className="text-slate-600 text-lg mb-8 text-center max-w-lg">
          {reason === 'student-only'
            ? 'GCS 학생만 이용할 수 있습니다.'
            : '정상적으로 로그인되었으나, 서비스를 이용할 수 있는 권한이 부여되지 않았습니다. 관리자에게 수강 승인을 요청하거나 고객센터에 문의해 주세요.'}
        </p>

        <div className="w-full max-w-md">
          <Card
            onClick={() => logout()}
            className="flex flex-col items-center p-6 text-center hover:border-rose-300 transition-colors cursor-pointer group hover:shadow-md"
          >
            <LogOut className="w-8 h-8 text-rose-500 mb-3 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold text-slate-900 mb-1">로그아웃</h3>
            <p className="text-sm text-slate-500">다른 계정으로 로그인</p>
          </Card>
        </div>

        <div className="mt-12 text-slate-400 text-sm">ID: {clientHostId}</div>
      </main>
    </div>
  );
}
