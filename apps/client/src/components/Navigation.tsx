'use client';

import React from 'react';
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
  GraduationCap,
  type LucideIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useAuth } from '@/context/auth-context';
import Link from 'next/link';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import { createNotificationsSse, notificationsApi } from '@/lib/api';
import type { NotificationItem } from '@/lib/types';
import { hasPrivilegedRole } from '@/lib/types';

const navLinkClass =
  'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground';
const notificationListLimit = 20;

type NavItem = {
  href: string;
  label: string;
  Icon: LucideIcon;
};

const navItems: NavItem[] = [
  { href: '/', label: '홈', Icon: Home },
  { href: '/daily-snippets', label: '일간 스니펫', Icon: Calendar },
  { href: '/weekly-snippets', label: '주간 스니펫', Icon: CalendarClock },
  { href: '/achievements', label: '업적', Icon: Medal },
];

type NavigationState = {
  isMenuOpen: boolean;
  isMobileNavOpen: boolean;
  isNotificationOpen: boolean;
  notifications: NotificationItem[];
  unreadCount: number;
  notificationsLoading: boolean;
};

type NavigationAction =
  | { type: 'toggle_menu' }
  | { type: 'close_menu' }
  | { type: 'toggle_mobile_nav' }
  | { type: 'set_mobile_nav_open'; open: boolean }
  | { type: 'set_notification_open'; open: boolean }
  | { type: 'set_notifications_loading'; loading: boolean }
  | {
      type: 'set_notifications_snapshot';
      notifications: NotificationItem[];
      unreadCount: number;
    }
  | { type: 'mark_notification_read'; notificationId: number }
  | { type: 'reset_notifications' };

const initialNavigationState: NavigationState = {
  isMenuOpen: false,
  isMobileNavOpen: false,
  isNotificationOpen: false,
  notifications: [],
  unreadCount: 0,
  notificationsLoading: false,
};

function navigationReducer(state: NavigationState, action: NavigationAction): NavigationState {
  switch (action.type) {
    case 'toggle_menu':
      return { ...state, isMenuOpen: !state.isMenuOpen };
    case 'close_menu':
      return { ...state, isMenuOpen: false };
    case 'toggle_mobile_nav':
      return { ...state, isMobileNavOpen: !state.isMobileNavOpen };
    case 'set_mobile_nav_open':
      return { ...state, isMobileNavOpen: action.open };
    case 'set_notification_open':
      return { ...state, isNotificationOpen: action.open };
    case 'set_notifications_loading':
      return { ...state, notificationsLoading: action.loading };
    case 'set_notifications_snapshot':
      return {
        ...state,
        notifications: action.notifications,
        unreadCount: action.unreadCount,
      };
    case 'mark_notification_read': {
      const target = state.notifications.find((item) => item.id === action.notificationId);
      const nextUnreadCount =
        target && !target.is_read ? Math.max(0, state.unreadCount - 1) : state.unreadCount;
      return {
        ...state,
        unreadCount: nextUnreadCount,
        notifications: state.notifications.map((item) =>
          item.id === action.notificationId ? { ...item, is_read: true } : item,
        ),
      };
    }
    case 'reset_notifications':
      return {
        ...state,
        isNotificationOpen: false,
        notifications: [],
        unreadCount: 0,
        notificationsLoading: false,
      };
    default:
      return state;
  }
}

function sortNotificationsByLatest(items: NotificationItem[]) {
  return [...items].sort((a, b) => {
    const timeDiff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    if (timeDiff !== 0) return timeDiff;
    return b.id - a.id;
  });
}

function formatNotificationTimestamp(createdAt: string) {
  return new Date(createdAt).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function notificationText(notification: NotificationItem) {
  if (notification.type === 'mention_in_comment') return '회원님을 멘션한 새 댓글이 있습니다.';
  if (notification.type === 'comment_on_my_snippet') return '회원님의 스니펫에 새 댓글이 달렸습니다.';
  return '참여한 스니펫에 새 댓글이 달렸습니다.';
}

function notificationLink(notification: NotificationItem) {
  const params = new URLSearchParams({ view: 'team' });

  if (typeof notification.comment_id === 'number') {
    params.set('highlight_comment_id', String(notification.comment_id));
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
}

type NavigationLinksProps = {
  className: string;
  onNavigate?: () => void;
};

function NavigationLinks({ className, onNavigate }: NavigationLinksProps) {
  const { user } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);
  const isProfessor = Boolean(user?.roles?.includes('교수'));

  return (
    <>
      {navItems.map(({ href, label, Icon }) => (
        <Link key={href} href={href} onClick={onNavigate} className={className}>
          <Icon className="h-5 w-5" />
          <span>{label}</span>
        </Link>
      ))}
      {hasAccess && isProfessor ? (
        <Link href="/professor" onClick={onNavigate} className={className}>
          <GraduationCap className="h-5 w-5" />
          <span>교수 멘토링</span>
        </Link>
      ) : null}
    </>
  );
}

type NotificationMenuProps = {
  notificationRef: React.RefObject<HTMLDivElement | null>;
  isOpen: boolean;
  unreadCount: number;
  notificationsLoading: boolean;
  notifications: NotificationItem[];
  onToggle: () => Promise<void>;
  onSelectNotification: (notification: NotificationItem) => Promise<void>;
};

function NotificationMenu({
  notificationRef,
  isOpen,
  unreadCount,
  notificationsLoading,
  notifications,
  onToggle,
  onSelectNotification,
}: NotificationMenuProps) {
  return (
    <div className="relative" ref={notificationRef}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          void onToggle();
        }}
        className="relative hidden cursor-pointer items-center rounded-full border border-border p-2 transition-colors hover:bg-accent md:flex"
        aria-label="알림 열기"
        aria-haspopup="menu"
        aria-expanded={isOpen}
      >
        <Bell className="h-4 w-4 text-muted-foreground" />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 min-w-[18px] rounded-full bg-primary px-1 text-center text-[10px] font-semibold leading-[18px] text-primary-foreground">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        ) : null}
      </button>

      <div
        className={cn(
          'absolute right-0 top-[calc(100%+12px)] z-50 hidden w-[340px] overflow-hidden rounded-xl border border-border bg-card py-2 shadow-sm md:block',
          isOpen ? 'md:block' : 'md:hidden',
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
                onClick={() => {
                  void onSelectNotification(notification);
                }}
                className={cn(
                  'mb-1 block rounded-lg px-3 py-2 transition-colors hover:bg-accent',
                  !notification.is_read && 'bg-primary/10',
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm text-foreground">{notificationText(notification)}</div>
                  <span
                    className={cn(
                      'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold',
                      notification.is_read
                        ? 'bg-muted text-muted-foreground'
                        : 'bg-primary/20 text-primary',
                    )}
                  >
                    {notification.is_read ? '읽음' : '안 읽음'}
                  </span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {formatNotificationTimestamp(notification.created_at)}
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

type UserMenuProps = {
  menuRef: React.RefObject<HTMLDivElement | null>;
  isOpen: boolean;
  userName?: string | null;
  userEmail?: string | null;
  userPicture?: string | null;
  onToggle: () => void;
  onClose: () => void;
  onLogout: () => void;
};

function UserMenu({
  menuRef,
  isOpen,
  userName,
  userEmail,
  userPicture,
  onToggle,
  onClose,
  onLogout,
}: UserMenuProps) {
  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onToggle();
        }}
        className="hidden cursor-pointer items-center rounded-full border border-border p-0.5 transition-colors hover:bg-accent md:flex"
        aria-label="사용자 메뉴 열기"
        aria-haspopup="menu"
        aria-expanded={isOpen}
      >
        <Avatar className="pointer-events-none h-8 w-8 shadow-sm">
          <AvatarImage src={userPicture ?? undefined} alt="" />
          <AvatarFallback className="bg-muted">
            <UserIcon className="h-4 w-4 text-muted-foreground" />
          </AvatarFallback>
        </Avatar>
      </button>

      <div
        className={cn(
          'absolute right-0 top-[calc(100%+12px)] z-50 hidden w-[280px] overflow-hidden rounded-xl border border-border bg-card py-2 shadow-sm md:block',
          isOpen ? 'md:block' : 'md:hidden',
        )}
      >
        <div className="mb-1 border-b border-border px-6 py-4">
          <div className="truncate text-left text-base font-semibold text-foreground">{userName}</div>
          <div className="mt-0.5 truncate text-left text-sm text-muted-foreground">{userEmail}</div>
        </div>

        <div className="px-3 py-1">
          <Link
            href="/settings"
            onClick={onClose}
            className="group flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-semibold text-foreground transition-colors hover:bg-accent"
          >
            <Settings className="h-4 w-4 text-muted-foreground transition-colors group-hover:text-primary" />
            설정
          </Link>

          <button
            type="button"
            onClick={onLogout}
            className="group flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-semibold text-destructive transition-colors hover:bg-destructive/10"
          >
            <LogOut className="h-4 w-4 text-destructive/70 transition-colors group-hover:text-destructive" />
            로그아웃
          </button>
        </div>
      </div>
    </div>
  );
}

type MobileNavMenuProps = {
  isOpen: boolean;
  isAuthenticated: boolean;
  unreadCount: number;
  onClose: () => void;
  onOpenNotifications: () => Promise<void>;
  onLogout: () => void;
};

function MobileNavMenu({
  isOpen,
  isAuthenticated,
  unreadCount,
  onClose,
  onOpenNotifications,
  onLogout,
}: MobileNavMenuProps) {
  return (
    <div
      id="mobile-nav-menu"
      className={cn('border-t border-border py-3 md:hidden', isOpen ? 'block' : 'hidden')}
    >
      <div className="flex flex-col gap-1">
        <NavigationLinks className={navLinkClass} onNavigate={onClose} />

        {isAuthenticated ? (
          <>
            <button
              type="button"
              onClick={() => {
                onClose();
                void onOpenNotifications();
              }}
              className={navLinkClass}
            >
              <Bell className="h-5 w-5" />
              <span>알림 {unreadCount > 0 ? `(${unreadCount})` : ''}</span>
            </button>
            <Link href="/settings" onClick={onClose} className={navLinkClass}>
              <Settings className="h-5 w-5" />
              <span>설정</span>
            </Link>
            <button
              type="button"
              onClick={() => {
                onClose();
                onLogout();
              }}
              className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
            >
              <LogOut className="h-5 w-5" />
              <span>로그아웃</span>
            </button>
          </>
        ) : (
          <Link href="/login" onClick={onClose} className="pt-2">
            <Button variant="default" size="default" className="w-full">
              로그인
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}

export function Navigation() {
  const { user, isAuthenticated, logout } = useAuth();
  const [state, dispatch] = React.useReducer(navigationReducer, initialNavigationState);
  const hasAccess = hasPrivilegedRole(user?.roles);
  const {
    isMenuOpen,
    isMobileNavOpen,
    isNotificationOpen,
    notifications,
    unreadCount,
    notificationsLoading,
  } = state;

  const menuRef = React.useRef<HTMLDivElement>(null);
  const notificationRef = React.useRef<HTMLDivElement>(null);

  const fetchNotificationSnapshot = React.useCallback(async () => {
    if (!hasAccess) {
      return {
        notifications: [] as NotificationItem[],
        unreadCount: 0,
      };
    }

    const [listRes, unreadRes] = await Promise.all([
      notificationsApi.list({ limit: notificationListLimit, offset: 0 }),
      notificationsApi.unreadCount(),
    ]);

    return {
      notifications: sortNotificationsByLatest(listRes.items),
      unreadCount: unreadRes.unread_count,
    };
  }, [hasAccess]);

  React.useEffect(() => {
    if (!isMenuOpen && !isNotificationOpen) return;

    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      if (menuRef.current && !menuRef.current.contains(target)) {
        dispatch({ type: 'close_menu' });
      }
      if (notificationRef.current && !notificationRef.current.contains(target)) {
        dispatch({ type: 'set_notification_open', open: false });
      }
    }

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [isMenuOpen, isNotificationOpen]);

  React.useEffect(() => {
    if (!isMobileNavOpen) return;

    function handleResize() {
      if (window.innerWidth >= 768) {
        dispatch({ type: 'set_mobile_nav_open', open: false });
      }
    }

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isMobileNavOpen]);

  React.useEffect(() => {
    if (!isAuthenticated || !hasAccess) {
      dispatch({ type: 'reset_notifications' });
      return;
    }

    let mounted = true;

    async function loadInitialNotifications() {
      try {
        dispatch({ type: 'set_notifications_loading', loading: true });
        const snapshot = await fetchNotificationSnapshot();
        if (!mounted) return;
        dispatch({
          type: 'set_notifications_snapshot',
          notifications: snapshot.notifications,
          unreadCount: snapshot.unreadCount,
        });
      } catch (error) {
        console.error('Failed to load notifications', error);
      } finally {
        if (mounted) {
          dispatch({ type: 'set_notifications_loading', loading: false });
        }
      }
    }

    loadInitialNotifications();

    const source = createNotificationsSse(async (event) => {
      try {
        const parsed = JSON.parse(event.data || '{}') as {
          notification_id?: number;
        };

        if (typeof parsed.notification_id !== 'number') return;

        const snapshot = await fetchNotificationSnapshot();
        if (!mounted) return;
        dispatch({
          type: 'set_notifications_snapshot',
          notifications: snapshot.notifications,
          unreadCount: snapshot.unreadCount,
        });
      } catch (error) {
        console.error('Failed to process notification event', error);
      }
    });

    source.onerror = () => {
      if (!mounted) return;
      if (
        source.readyState === EventSource.CONNECTING ||
        source.readyState === EventSource.CLOSED
      ) {
        return;
      }
    };

    return () => {
      mounted = false;
      source.close();
    };
  }, [isAuthenticated, hasAccess, fetchNotificationSnapshot]);

  const handleOpenNotifications = React.useCallback(async () => {
    const nextOpen = !isNotificationOpen;
    dispatch({ type: 'set_notification_open', open: nextOpen });

    if (!nextOpen || !hasAccess) return;

    try {
      dispatch({ type: 'set_notifications_loading', loading: true });
      const snapshot = await fetchNotificationSnapshot();
      dispatch({
        type: 'set_notifications_snapshot',
        notifications: snapshot.notifications,
        unreadCount: snapshot.unreadCount,
      });
    } catch (error) {
      console.error('Failed to refresh notifications', error);
    } finally {
      dispatch({ type: 'set_notifications_loading', loading: false });
    }
  }, [fetchNotificationSnapshot, hasAccess, isNotificationOpen]);

  const handleSelectNotification = React.useCallback(async (notification: NotificationItem) => {
    dispatch({ type: 'set_notification_open', open: false });

    if (notification.is_read) return;

    try {
      await notificationsApi.markRead(notification.id);
      dispatch({ type: 'mark_notification_read', notificationId: notification.id });
    } catch (error) {
      console.error('Failed to mark one notification read', error);
    }
  }, []);

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
              <NavigationLinks className={navLinkClass} />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => dispatch({ type: 'toggle_mobile_nav' })}
              className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground md:hidden"
              aria-label="모바일 메뉴 열기"
              aria-controls="mobile-nav-menu"
              aria-expanded={isMobileNavOpen}
            >
              {isMobileNavOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            {isAuthenticated ? (
              <div className="flex items-center gap-2 md:gap-4">
                <NotificationMenu
                  notificationRef={notificationRef}
                  isOpen={isNotificationOpen}
                  unreadCount={unreadCount}
                  notificationsLoading={notificationsLoading}
                  notifications={notifications}
                  onToggle={handleOpenNotifications}
                  onSelectNotification={handleSelectNotification}
                />

                <UserMenu
                  menuRef={menuRef}
                  isOpen={isMenuOpen}
                  userName={user?.name}
                  userEmail={user?.email}
                  userPicture={user?.picture ?? null}
                  onToggle={() => dispatch({ type: 'toggle_menu' })}
                  onClose={() => dispatch({ type: 'close_menu' })}
                  onLogout={() => {
                    dispatch({ type: 'close_menu' });
                    logout();
                  }}
                />
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

        <MobileNavMenu
          isOpen={isMobileNavOpen}
          isAuthenticated={isAuthenticated}
          unreadCount={unreadCount}
          onClose={() => dispatch({ type: 'set_mobile_nav_open', open: false })}
          onOpenNotifications={handleOpenNotifications}
          onLogout={logout}
        />
      </div>
    </nav>
  );
}
