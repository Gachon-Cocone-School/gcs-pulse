'use client';

import React from 'react';
import { API_URL } from '@/lib/api';

export default function LoginPage() {
  const handleGoogleLogin = () => {
    window.location.href = `${API_URL}/auth/google/login`;
  };

  return (
    <div className="min-h-screen w-full bg-slate-50 flex flex-col items-center justify-center p-6 font-sans">
      {/* 1번 이미지와 동일한 카드 레이아웃 */}
      <div className="w-full max-w-[440px] bg-white rounded-[32px] shadow-[0_25px_50px_-12px_rgba(0,0,0,0.08)] px-10 py-14 flex flex-col items-center text-center border border-slate-100">
        
        {/* 로고 영역 */}
        <div className="mb-8 flex justify-center">
          <img 
            src="/logo.svg" 
            alt="Logo" 
            className="h-12 w-auto block"
          />
        </div>

        {/* 텍스트 영역 */}
        <h1 className="text-2xl font-bold text-slate-900 mb-2 mt-0 text-center">
          환영합니다
        </h1>
        <p className="text-[15px] text-slate-500 mb-10 mt-0 text-center">
          가천 코코네 스쿨에 로그인하세요
        </p>

        {/* Google 로그인 버튼 */}
        <button
          onClick={handleGoogleLogin}
          className="w-full p-4 bg-white border-2 border-slate-200 rounded-2xl cursor-pointer flex items-center justify-center gap-3 text-base font-bold text-slate-700 transition-all hover:border-[#d5386f] hover:bg-[#fff1f6] outline-none"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
          </svg>
          Google 계정으로 로그인
        </button>

        {/* 하단 구분선 및 안내 문구 */}
        <div className="w-full mt-10 pt-8 border-t border-slate-100">
          <p className="text-sm text-slate-400 leading-relaxed m-0 text-center">
            학생과 교직원은 학교 Google 계정으로 로그인 해야 합니다.
          </p>
        </div>
      </div>

      {/* 푸터 영역 */}
      <footer className="mt-12 text-[13px] text-slate-400 font-medium">
        © 2026 Gachon Cocone School. All rights reserved.
      </footer>
    </div>
  );
}
