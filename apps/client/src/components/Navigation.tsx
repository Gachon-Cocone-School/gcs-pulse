'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Home,
  Settings,
  LogOut,
  User as UserIcon,
  Calendar,
  CalendarClock,
  Medal,
  Menu,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useAuth } from '@/context/auth-context';
import Link from 'next/link';
import Image from 'next/image';
import { cn } from '@/lib/utils';

const navLinkClass =
  'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground';

export function Navigation() {
  const { user, isAuthenticated, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
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

  useEffect(() => {
    if (!isMobileNavOpen) return;

    function handleResize() {
      if (window.innerWidth >= 768) {
        setIsMobileNavOpen(false);
      }
    }

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isMobileNavOpen]);

  return (
    <nav className="relative z-40 border-b border-border bg-card">
      <div className="mx-auto max-w-7xl px-6">
        <div className="flex h-16 items-center justify-between">
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

            <div className="hidden items-center gap-1 md:flex">
              <Link href="/" className={navLinkClass}>
                <Home className="h-5 w-5" />
                <span>홈</span>
              </Link>
              <Link href="/daily-snippets" className={navLinkClass}>
                <Calendar className="h-5 w-5" />
                <span>일간 스니펫</span>
              </Link>
              <Link href="/weekly-snippets" className={navLinkClass}>
                <CalendarClock className="h-5 w-5" />
                <span>주간 스니펫</span>
              </Link>
              <Link href="/achievements" className={navLinkClass}>
                <Medal className="h-5 w-5" />
                <span>업적</span>
              </Link>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsMobileNavOpen((prev) => !prev)}
              className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground md:hidden"
              aria-label="모바일 메뉴 열기"
              aria-controls="mobile-nav-menu"
              aria-expanded={isMobileNavOpen}
            >
              {isMobileNavOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            {isAuthenticated ? (
              <div className="flex items-center gap-4">
                <div className="relative" ref={menuRef}>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsMenuOpen((prev) => !prev);
                    }}
                    className="hidden cursor-pointer items-center rounded-full border border-border p-0.5 transition-colors hover:bg-accent md:flex"
                    aria-label="사용자 메뉴 열기"
                    aria-haspopup="menu"
                    aria-expanded={isMenuOpen}
                  >
                    <Avatar className="pointer-events-none h-8 w-8 shadow-sm">
                      <AvatarImage src={user?.picture} alt="" />
                      <AvatarFallback className="bg-muted">
                        <UserIcon className="h-4 w-4 text-muted-foreground" />
                      </AvatarFallback>
                    </Avatar>
                  </button>

                  <div
                    className={cn(
                      'absolute right-0 top-[calc(100%+12px)] z-50 hidden w-[280px] overflow-hidden rounded-xl border border-border bg-card py-2 shadow-sm md:block',
                      isMenuOpen ? 'md:block' : 'md:hidden',
                    )}
                  >
                    <div className="mb-1 border-b border-border px-6 py-4">
                      <div className="truncate text-left text-base font-semibold text-foreground">{user?.name}</div>
                      <div className="mt-0.5 truncate text-left text-sm text-muted-foreground">{user?.email}</div>
                    </div>

                    <div className="px-3 py-1">
                      <Link
                        href="/settings"
                        onClick={() => setIsMenuOpen(false)}
                        className="group flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-semibold text-foreground transition-colors hover:bg-accent"
                      >
                        <Settings className="h-4 w-4 text-muted-foreground transition-colors group-hover:text-primary" />
                        설정
                      </Link>

                      <button
                        type="button"
                        onClick={() => {
                          setIsMenuOpen(false);
                          logout();
                        }}
                        className="group flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-semibold text-destructive transition-colors hover:bg-destructive/10"
                      >
                        <LogOut className="h-4 w-4 text-destructive/70 transition-colors group-hover:text-destructive" />
                        로그아웃
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <Link href="/login">
                <Button variant="default" size="default" className="px-6">
                  로그인
                </Button>
              </Link>
            )}
          </div>
        </div>

        <div
          id="mobile-nav-menu"
          className={cn(
            'border-t border-border py-3 md:hidden',
            isMobileNavOpen ? 'block' : 'hidden',
          )}
        >
          <div className="flex flex-col gap-1">
            <Link
              href="/"
              onClick={() => setIsMobileNavOpen(false)}
              className={navLinkClass}
            >
              <Home className="h-5 w-5" />
              <span>홈</span>
            </Link>
            <Link
              href="/daily-snippets"
              onClick={() => setIsMobileNavOpen(false)}
              className={navLinkClass}
            >
              <Calendar className="h-5 w-5" />
              <span>일간 스니펫</span>
            </Link>
            <Link
              href="/weekly-snippets"
              onClick={() => setIsMobileNavOpen(false)}
              className={navLinkClass}
            >
              <CalendarClock className="h-5 w-5" />
              <span>주간 스니펫</span>
            </Link>
            <Link
              href="/achievements"
              onClick={() => setIsMobileNavOpen(false)}
              className={navLinkClass}
            >
              <Medal className="h-5 w-5" />
              <span>업적</span>
            </Link>

            {isAuthenticated ? (
              <>
                <Link
                  href="/settings"
                  onClick={() => setIsMobileNavOpen(false)}
                  className={navLinkClass}
                >
                  <Settings className="h-5 w-5" />
                  <span>설정</span>
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    setIsMobileNavOpen(false);
                    logout();
                  }}
                  className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
                >
                  <LogOut className="h-5 w-5" />
                  <span>로그아웃</span>
                </button>
              </>
            ) : (
              <Link href="/login" onClick={() => setIsMobileNavOpen(false)} className="pt-2">
                <Button variant="default" size="default" className="w-full">
                  로그인
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
