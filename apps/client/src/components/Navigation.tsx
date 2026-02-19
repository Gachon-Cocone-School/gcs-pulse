'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Home, BookOpen, BarChart3, Settings, Bell, Search, LogOut, User as UserIcon, Shield, Calendar, CalendarClock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useAuth } from '@/context/auth-context';
import Link from 'next/link';
import Image from 'next/image';

export function Navigation() {
  const { user, isAuthenticated, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }
    if (isMenuOpen) {
      document.addEventListener('click', handleClickOutside);
    }
    return () => document.removeEventListener('click', handleClickOutside);
  }, [isMenuOpen]);

  return (
    <nav className="bg-white border-b border-slate-200 relative" style={{ zIndex: 9999 }}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-3">
              <Image
                src="/logo.svg"
                alt="Gachon Cocone School"
                width={160}
                height={32}
                className="h-8 w-auto"
                priority
              />
            </Link>
            
            <div className="hidden md:flex items-center gap-1">
              <Link href="/" className="flex items-center gap-2 px-4 py-2 text-slate-700 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors">
                <Home className="w-5 h-5" />
                <span className="font-medium text-sm">홈</span>
              </Link>
              <Link href="/daily-snippets" className="flex items-center gap-2 px-4 py-2 text-slate-700 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors">
                <Calendar className="w-5 h-5" />
                <span className="font-medium text-sm">일간 스니펫</span>
              </Link>
              <Link href="/weekly-snippets" className="flex items-center gap-2 px-4 py-2 text-slate-700 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors">
                <CalendarClock className="w-5 h-5" />
                <span className="font-medium text-sm">주간 스니펫</span>
              </Link>
            </div>
          </div>
          
          <div className="flex items-center gap-3">

            
            {isAuthenticated ? (
              <div className="flex items-center gap-4">
                <button className="p-2 text-slate-400 hover:text-primary-500 transition-colors relative outline-none focus:outline-none">
                  <Bell className="w-5 h-5" />
                  <div className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-white" />
                </button>
                
                <div className="relative" ref={menuRef}>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsMenuOpen((prev) => !prev);
                    }}
                    className="flex items-center cursor-pointer p-0.5 rounded-full hover:bg-slate-50 transition-all border border-slate-100 hover:border-slate-200"
                    aria-label="사용자 메뉴 열기"
                    aria-haspopup="menu"
                    aria-expanded={isMenuOpen}
                  >
                    <Avatar className="w-8 h-8 shadow-sm pointer-events-none">
                      <AvatarImage src={user?.picture} alt="" />
                      <AvatarFallback className="bg-slate-100">
                        <UserIcon className="w-4 h-4 text-slate-400" />
                      </AvatarFallback>
                    </Avatar>
                  </button>
                  
                  {/* The Menu - Fixed padding and alignment issues */}
                  <div style={{
                    display: isMenuOpen ? 'block' : 'none',
                    position: 'absolute',
                    right: 0,
                    top: 'calc(100% + 12px)',
                    width: '280px',
                    backgroundColor: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '24px',
                    boxShadow: '0 20px 40px -10px rgba(0, 0, 0, 0.12)',
                    padding: '8px 0',
                    zIndex: 100000,
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      padding: '16px 24px',
                      borderBottom: '1px solid #f8fafc',
                      marginBottom: '4px'
                    }}>
                      <div style={{
                        fontWeight: '700',
                        color: '#0f172a',
                        fontSize: '16px',
                        lineHeight: '1.4',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        textAlign: 'left'
                      }}>{user?.name}</div>
                      <div style={{
                        fontSize: '13px',
                        color: '#94a3b8',
                        marginTop: '2px',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        textAlign: 'left'
                      }}>{user?.email}</div>
                    </div>
                    
                    <div style={{ padding: '4px 12px' }}>
                      <Link
                        href="/settings"
                        onClick={() => setIsMenuOpen(false)}
                        className="w-full text-left px-4 py-3 text-slate-600 hover:bg-slate-50 transition-colors flex items-center gap-3 rounded-[16px] text-sm font-semibold group"
                      >
                        <Settings className="w-4.5 h-4.5 text-slate-400 group-hover:text-primary-600" />
                        설정
                      </Link>

                      <button
                        onClick={() => {
                          setIsMenuOpen(false);
                          logout();
                        }}
                        className="w-full text-left px-4 py-3 text-rose-500 hover:bg-rose-50 transition-colors flex items-center gap-3 rounded-[16px] text-sm font-semibold group"
                      >
                        <LogOut className="w-4.5 h-4.5 text-rose-400 group-hover:text-rose-600" />
                        로그아웃
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <Link href="/login">
                <Button variant="default" size="default" className="rounded-xl px-6">로그인</Button>
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}