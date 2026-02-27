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
  Bell,
  Menu,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useAuth } from '@/context/auth-context';
import Link from 'next/link';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import { createNotificationsSse, notificationsApi } from '@/lib/api';
import type { NotificationItem } from '@/lib/types';

const navLinkClass =
  'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground';

export function Navigation() {
  const { user, isAuthenticated, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const notificationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setIsNotificationOpen(false);
      }
    }

    if (isMenuOpen || isNotificationOpen) {
      document.addEventListener('click', handleClickOutside);
    }

    return () => document.removeEventListener('click', handleClickOutside);
  }, [isMenuOpen, isNotificationOpen]);

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

  useEffect(() => {
    if (!isAuthenticated) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    let mounted = true;

    async function loadInitialNotifications() {
      try {
        setNotificationsLoading(true);
        const [listRes, unreadRes] = await Promise.all([
          notificationsApi.list({ limit: 10, offset: 0 }),
          notificationsApi.unreadCount(),
        ]);
        if (!mounted) return;
        setNotifications(listRes.items);
        setUnreadCount(unreadRes.unread_count);
      } catch (error) {
        console.error('Failed to load notifications', error);
      } finally {
        if (mounted) setNotificationsLoading(false);
      }
    }

    loadInitialNotifications();

    const source = createNotificationsSse(async (event) => {
      try {
        const parsed = JSON.parse(event.data || '{}') as {
          notification_id?: number;
        };

        if (typeof parsed.notification_id === 'number') {
          const listRes = await notificationsApi.list({ limit: 10, offset: 0 });
          const unreadRes = await notificationsApi.unreadCount();
          if (!mounted) return;
          setNotifications(listRes.items);
          setUnreadCount(unreadRes.unread_count);
        }
      } catch (error) {
        console.error('Failed to process notification event', error);
      }
    });

    source.onerror = (error) => {
      console.error('Notifications SSE error', error);
    };

    return () => {
      mounted = false;
      source.close();
    };
  }, [isAuthenticated]);

  const notificationLink = (notification: NotificationItem) => {
    const params = new URLSearchParams({ view: 'team' });
    if (notification.type === 'mention_in_comment') {
      params.set('highlight_comment_id', String(notification.comment_id ?? ''));
    }

    if (notification.daily_snippet_id) {
      params.set('id', String(notification.daily_snippet_id));
      return `/daily-snippets?${params.toString()}`;
    }

    if (notification.weekly_snippet_id) {
      params.set('id', String(notification.weekly_snippet_id));
      return `/weekly-snippets?${params.toString()}`;
    }

    return '/';
  };

  const notificationText = (notification: NotificationItem) => {
    if (notification.type === 'mention_in_comment') return '회원님을 멘션한 새 댓글이 있습니다.';
    if (notification.type === 'comment_on_my_snippet') return '회원님의 스니펫에 새 댓글이 달렸습니다.';
    return '참여한 스니펫에 새 댓글이 달렸습니다.';
  };

  const handleOpenNotifications = async () => {
    setIsNotificationOpen((prev) => !prev);
    if (unreadCount > 0) {
      try {
        await notificationsApi.markAllRead();
        setUnreadCount(0);
        setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
      } catch (error) {
        console.error('Failed to mark notifications as read', error);
      }
    }
  };

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
              <div className="flex items-center gap-2 md:gap-4">
                <div className="relative" ref={notificationRef}>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleOpenNotifications();
                    }}
                    className="relative hidden cursor-pointer items-center rounded-full border border-border p-2 transition-colors hover:bg-accent md:flex"
                    aria-label="알림 열기"
                    aria-haspopup="menu"
                    aria-expanded={isNotificationOpen}
                  >
                    <Bell className="h-4 w-4 text-muted-foreground" />
                    {unreadCount > 0 ? (
                      <span className="absolute -right-1 -top-1 min-w-[18px] rounded-full bg-rose-500 px-1 text-center text-[10px] font-semibold leading-[18px] text-white">
                        {unreadCount > 99 ? '99+' : unreadCount}
                      </span>
                    ) : null}
                  </button>

                  <div
                    className={cn(
                      'absolute right-0 top-[calc(100%+12px)] z-50 hidden w-[340px] overflow-hidden rounded-xl border border-border bg-card py-2 shadow-sm md:block',
                      isNotificationOpen ? 'md:block' : 'md:hidden',
                    )}
                  >
                    <div className="mb-1 border-b border-border px-4 py-3">
                      <div className="text-left text-sm font-semibold text-foreground">알림</div>
                    </div>

                    <div className="max-h-96 overflow-y-auto px-2 py-1">
                      {notificationsLoading ? (
                        <div className="px-3 py-6 text-center text-sm text-muted-foreground">불러오는 중...</div>
                      ) : notifications.length === 0 ? (
                        <div className="px-3 py-6 text-center text-sm text-muted-foreground">새 알림이 없습니다.</div>
                      ) : (
                        notifications.map((notification) => (
                          <Link
                            key={notification.id}
                            href={notificationLink(notification)}
                            onClick={async () => {
                              setIsNotificationOpen(false);
                              if (!notification.is_read) {
                                try {
                                  await notificationsApi.markRead(notification.id);
                                  setNotifications((prev) =>
                                    prev.map((item) =>
                                      item.id === notification.id
                                        ? { ...item, is_read: true }
                                        : item,
                                    ),
                                  );
                                } catch (error) {
                                  console.error('Failed to mark one notification read', error);
                                }
                              }
                            }}
                            className={cn(
                              'mb-1 block rounded-lg px-3 py-2 transition-colors hover:bg-accent',
                              !notification.is_read && 'bg-rose-50/60',
                            )}
                          >
                            <div className="text-sm text-foreground">{notificationText(notification)}</div>
                          </Link>
                        ))
                      )}
                    </div>
                  </div>
                </div>

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
                <button
                  type="button"
                  onClick={async () => {
                    setIsMobileNavOpen(false);
                    try {
                      await notificationsApi.markAllRead();
                      setUnreadCount(0);
                      setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
                    } catch (error) {
                      console.error('Failed to mark notifications as read on mobile', error);
                    }
                  }}
                  className={navLinkClass}
                >
                  <Bell className="h-5 w-5" />
                  <span>알림 {unreadCount > 0 ? `(${unreadCount})` : ''}</span>
                </button>
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
