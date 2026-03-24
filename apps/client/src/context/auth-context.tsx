'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { ApiError, api } from '@/lib/api';
import { resetCsrfToken } from '@/lib/csrf';
import type { AuthContextType, AuthStatusResponse, AuthUser } from '@/lib/types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_CACHE_TTL_MS = process.env.NEXT_PUBLIC_E2E_TEST === 'true' ? 30 * 60 * 1000 : 0;
let authStatusCache: { data: AuthStatusResponse; fetchedAt: number } | null = null;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const hasLoadedAuthRef = useRef(false);

  const checkAuth = useCallback(async () => {
    setIsLoading(true);
    setAuthError(null);

    if (AUTH_CACHE_TTL_MS > 0 && authStatusCache) {
      const isFresh = Date.now() - authStatusCache.fetchedAt < AUTH_CACHE_TTL_MS;
      if (isFresh) {
        setIsAuthenticated(authStatusCache.data.authenticated);
        setUser(authStatusCache.data.user);
        hasLoadedAuthRef.current = true;
        setIsLoading(false);
        return;
      }
    }

    try {
      const data = await api.get<AuthStatusResponse>('/auth/me');
      if (AUTH_CACHE_TTL_MS > 0) {
        authStatusCache = { data, fetchedAt: Date.now() };
      }
      setIsAuthenticated(data.authenticated);
      setUser(data.user);
      hasLoadedAuthRef.current = true;
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        authStatusCache = null;
        resetCsrfToken();
        setIsAuthenticated(false);
        setUser(null);
      } else if (error instanceof ApiError && error.status === 0) {
        setIsAuthenticated(false);
        setUser(null);
        setAuthError('API 서버에 연결할 수 없습니다. 서버 상태를 확인한 뒤 다시 시도해 주세요.');
      } else {
        setAuthError('인증 상태를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.');
        console.error('Failed to fetch auth status');
      }
      hasLoadedAuthRef.current = true;
    } finally {
      if (hasLoadedAuthRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  const logout = async () => {
    try {
      await api.post('/auth/logout');
      authStatusCache = null;
      resetCsrfToken();
      setIsAuthenticated(false);
      setUser(null);
      // Optional: Redirect to login or home
      window.location.href = '/';
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // 다른 앱 갔다가 브라우저로 복귀 시 세션 재확인
  // 모바일에서 JS 타이머가 백그라운드에서 중지되므로 interval 대신 visibilitychange 사용
  // 1분 쓰로틀: 짧은 앱 전환에서 과도한 호출 방지
  useEffect(() => {
    const THROTTLE_MS = 60 * 1000;
    let lastChecked = Date.now();
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && Date.now() - lastChecked > THROTTLE_MS) {
        lastChecked = Date.now();
        checkAuth();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [checkAuth]);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, authError, checkAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
