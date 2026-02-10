'use client';

import React from 'react';
import Link from 'next/link';
import { ShieldAlert, AlertTriangle, Home, RefreshCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface ErrorViewProps {
  code?: number | string;
  title: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorView({ code, title, message, onRetry }: ErrorViewProps) {
  const Icon = code === 403 || code === 401 ? ShieldAlert : AlertTriangle;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      <main className="max-w-lg w-full flex flex-col items-center">
        <div className="w-24 h-24 bg-rose-100 rounded-full flex items-center justify-center mb-8 animate-in fade-in zoom-in duration-500">
          <Icon className="w-12 h-12 text-rose-600" />
        </div>

        <div className="text-center mb-10">
          {code && (
            <span className="text-sm font-bold tracking-widest text-rose-500 uppercase mb-2 block">
              Error {code}
            </span>
          )}
          <h1 className="text-3xl font-bold text-slate-900 mb-4">{title}</h1>
          <p className="text-slate-600 text-lg leading-relaxed">
            {message}
          </p>
        </div>

        <Card className="w-full p-1 bg-white/50 backdrop-blur-md border-white/40 shadow-sm rounded-xl overflow-hidden mb-8">
          <div className="grid sm:grid-cols-2 gap-1">
            <Button
              asChild
              variant="ghost"
              className="h-14 rounded-lg flex items-center justify-center gap-2 text-slate-600 hover:text-rose-600 hover:bg-rose-50 transition-all"
            >
              <Link href="/">
                <Home className="w-5 h-5" />
                <span>홈으로 돌아가기</span>
              </Link>
            </Button>

            {onRetry ? (
              <Button
                variant="ghost"
                onClick={onRetry}
                className="h-14 rounded-lg flex items-center justify-center gap-2 text-slate-600 hover:text-rose-600 hover:bg-rose-50 transition-all"
              >
                <RefreshCcw className="w-5 h-5" />
                <span>다시 시도하기</span>
              </Button>
            ) : (
              <Button
                asChild
                variant="ghost"
                className="h-14 rounded-lg flex items-center justify-center gap-2 text-slate-600 hover:text-rose-600 hover:bg-rose-50 transition-all"
              >
                <Link href="/support">
                  <AlertTriangle className="w-5 h-5" />
                  <span>고객센터 문의</span>
                </Link>
              </Button>
            )}
          </div>
        </Card>

        <p className="text-slate-400 text-sm">
          문제가 지속되면 시스템 관리자에게 문의해 주세요.
        </p>
      </main>
    </div>
  );
}
