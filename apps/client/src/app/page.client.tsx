'use client';

import { useEffect, useReducer } from 'react';
import { redirect, useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { ApiError, api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, User as UserIcon } from 'lucide-react';
import LoginPageClient from './login/LoginPageClient';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Navigation } from '@/components/Navigation';
import type {
  LeaderboardItem,
  LeaderboardPeriod,
  LeaderboardResponse,
  RecentAchievementGrantItem,
  RecentAchievementGrantsResponse,
  UserConsent,
} from '@/lib/types/auth';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { hasPrivilegedRole } from '@/lib/types';
import {
  achievementAvatarFrameClass,
  achievementAvatarImageClass,
  achievementCardClass,
  rarityBadgeClassMap,
  rarityLabelMap,
  resolveRecentAchievementRarity,
} from '@/lib/achievementUi';

interface Term {
  id: number;
  is_required: boolean;
}



type HomeState = {
  checkingConsents: boolean;
  mustAgreeTerms: boolean;
  period: LeaderboardPeriod;
  leaderboard: LeaderboardResponse | null;
  leaderboardLoading: boolean;
  leaderboardError: string | null;
  recentAchievements: RecentAchievementGrantItem[];
  recentAchievementsLoading: boolean;
  recentAchievementsError: string | null;
};

type HomeAction =
  | { type: 'CONSENT_CHECKED'; payload: boolean }
  | { type: 'SET_PERIOD'; payload: LeaderboardPeriod }
  | { type: 'LEADERBOARD_FETCH_START' }
  | { type: 'LEADERBOARD_FETCH_SUCCESS'; payload: LeaderboardResponse }
  | { type: 'LEADERBOARD_FETCH_FAILURE'; payload: string }
  | { type: 'RECENT_ACHIEVEMENTS_FETCH_START' }
  | { type: 'RECENT_ACHIEVEMENTS_FETCH_SUCCESS'; payload: RecentAchievementGrantItem[] }
  | { type: 'RECENT_ACHIEVEMENTS_FETCH_FAILURE'; payload: string };

const initialHomeState: HomeState = {
  checkingConsents: true,
  mustAgreeTerms: false,
  period: 'daily',
  leaderboard: null,
  leaderboardLoading: false,
  leaderboardError: null,
  recentAchievements: [],
  recentAchievementsLoading: false,
  recentAchievementsError: null,
};

function homeReducer(state: HomeState, action: HomeAction): HomeState {
  switch (action.type) {
    case 'CONSENT_CHECKED':
      return {
        ...state,
        checkingConsents: false,
        mustAgreeTerms: action.payload,
      };
    case 'SET_PERIOD':
      return {
        ...state,
        period: action.payload,
      };
    case 'LEADERBOARD_FETCH_START':
      return {
        ...state,
        leaderboardLoading: true,
        leaderboardError: null,
      };
    case 'LEADERBOARD_FETCH_SUCCESS':
      return {
        ...state,
        leaderboardLoading: false,
        leaderboard: action.payload,
      };
    case 'LEADERBOARD_FETCH_FAILURE':
      return {
        ...state,
        leaderboardLoading: false,
        leaderboardError: action.payload,
      };
    case 'RECENT_ACHIEVEMENTS_FETCH_START':
      return {
        ...state,
        recentAchievementsLoading: true,
        recentAchievementsError: null,
      };
    case 'RECENT_ACHIEVEMENTS_FETCH_SUCCESS':
      return {
        ...state,
        recentAchievementsLoading: false,
        recentAchievementsError: null,
        recentAchievements: action.payload,
      };
    case 'RECENT_ACHIEVEMENTS_FETCH_FAILURE':
      return {
        ...state,
        recentAchievementsLoading: false,
        recentAchievementsError: action.payload,
      };
    default:
      return state;
  }
}

function LeaderboardList({ items }: { items: LeaderboardItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">표시할 랭킹 데이터가 없습니다.</p>;
  }

  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={`${item.participant_type}-${item.participant_id}`} className="rounded-lg border border-border bg-card/80 px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-foreground">
                #{item.rank} {item.participant_name}
              </p>
              <p className="text-xs text-muted-foreground">
                {item.participant_type === 'team' ? '팀' : '개인'}
                {item.participant_type === 'team' && item.member_count != null ? ` · ${item.member_count}명` : ''}
                {item.participant_type === 'team' && item.submitted_count != null ? ` · 제출 ${item.submitted_count}명` : ''}
              </p>
            </div>
            <p className="text-sm font-bold text-destructive">{item.score.toFixed(2)}점</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function RecentAchievementsBoard({ items }: { items: RecentAchievementGrantItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">최근 공개 가능한 업적 지급 내역이 없습니다.</p>;
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const rarity = resolveRecentAchievementRarity(item);
        return (
          <li key={item.grant_id} className={achievementCardClass}>
            <div className="flex items-start gap-3">
              <Avatar className={`h-12 w-12 rounded-md shrink-0 ${achievementAvatarFrameClass}`}>
                <AvatarImage src={item.badge_image_url} alt={item.achievement_name} className={achievementAvatarImageClass} />
                <AvatarFallback className="rounded-md bg-muted">
                  <UserIcon className="h-4 w-4 text-muted-foreground" />
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-foreground">
                    {item.user_name} · {item.achievement_name}
                  </p>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${rarityBadgeClassMap[rarity]}`}>
                    {rarityLabelMap[rarity]}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{item.achievement_description}</p>
                <p className="text-xs text-muted-foreground mt-2">획득 일자: {new Date(item.granted_at).toLocaleDateString('ko-KR')}</p>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export default function HomePageClient() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [state, dispatch] = useReducer(homeReducer, initialHomeState);
  const router = useRouter();
  const hasAccess = hasPrivilegedRole(user?.roles);

  useEffect(() => {
    if (isLoading) return;

    const verifyConsents = async () => {
      let nextMustAgreeTerms = false;

      try {
        if (isAuthenticated && user) {
          const terms = await api.get<Term[]>('/terms');
          const requiredTermIds = terms.filter((t) => t.is_required).map((t) => t.id);
          const agreedTermIds = (user.consents as UserConsent[]).map((c) => c.term_id);
          const allAgreed = requiredTermIds.every((id) => agreedTermIds.includes(id));
          nextMustAgreeTerms = !allAgreed;
        }
      } catch (error) {
        console.error('Failed to verify consents:', error);
      } finally {
        dispatch({ type: 'CONSENT_CHECKED', payload: nextMustAgreeTerms });
      }
    };

    verifyConsents();
  }, [isAuthenticated, user, isLoading]);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      if (!isAuthenticated || !hasAccess) return;

      dispatch({ type: 'LEADERBOARD_FETCH_START' });
      try {
        const data = await api.get<LeaderboardResponse>(`/leaderboards?period=${state.period}`);
        dispatch({ type: 'LEADERBOARD_FETCH_SUCCESS', payload: data });
      } catch (error: unknown) {
        console.error('Failed to fetch leaderboard:', error);
        dispatch({
          type: 'LEADERBOARD_FETCH_FAILURE',
          payload: '리더보드를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.',
        });
      }
    };

    fetchLeaderboard();
  }, [isAuthenticated, hasAccess, state.period]);

  useEffect(() => {
    const fetchRecentAchievements = async () => {
      if (!isAuthenticated || !hasAccess) return;

      dispatch({ type: 'RECENT_ACHIEVEMENTS_FETCH_START' });
      try {
        const data = await api.get<RecentAchievementGrantsResponse>('/achievements/recent?limit=20');
        dispatch({ type: 'RECENT_ACHIEVEMENTS_FETCH_SUCCESS', payload: data.items ?? [] });
      } catch (error: unknown) {
        console.error('Failed to fetch recent achievements:', error);
        if (error instanceof ApiError && error.status === 404) {
          dispatch({ type: 'RECENT_ACHIEVEMENTS_FETCH_SUCCESS', payload: [] });
        } else {
          dispatch({
            type: 'RECENT_ACHIEVEMENTS_FETCH_FAILURE',
            payload: '최근 업적 공지를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.',
          });
        }
      }
    };

    fetchRecentAchievements();
  }, [isAuthenticated, hasAccess]);

  // 1. 로딩 중
  if (isLoading || (isAuthenticated && state.checkingConsents)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-[var(--sys-spinner-indicator)] animate-spin" />
          <p className="text-muted-foreground font-medium">유저 정보를 확인 중입니다...</p>
        </div>
      </div>
    );
  }

  // 2. 미인증 사용자 -> 로그인 페이지 표시
  if (!isAuthenticated) {
    return <LoginPageClient />;
  }

  // 3. 권한 체크 -> gcs/교수/admin만 접근 허용
  if (!hasAccess) {
    return <AccessDeniedView reason="student-only" />;
  }

  // 4. 약관 동의 필요 사용자
  if (state.mustAgreeTerms) {
    redirect('/terms');
  }

  // 5. 모든 조건 통과 -> 메인 대시보드 표시 (Minimal Hero)
  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="flex flex-col items-center justify-center p-4 md:py-10">
        <div className="w-full max-w-5xl space-y-8 animate-entrance">
          <div className="text-center space-y-4 glass-card p-8 md:p-10 rounded-xl">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-foreground">
              <span className="premium-gradient-text">GCS Pulse</span>
            </h1>
            <p className="text-xl text-muted-foreground leading-relaxed">
              작은 기록이 모여
              <span className="font-semibold text-foreground"> 특별한 성장</span>을 만듭니다.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-card p-8 md:p-10 rounded-xl text-center space-y-6">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">일간 스니펫</h2>
              <p className="text-muted-foreground leading-relaxed">하루를 정리하며 꾸준한 성장을 기록해보세요.</p>
              <Button
                size="lg"
                className="w-full text-base px-6 py-5 h-auto shadow-lg hover:shadow-xl transition-all rounded-full"
                onClick={() => router.push('/daily-snippets')}
              >
                일간 스니펫
              </Button>
            </div>

            <div className="glass-card p-8 md:p-10 rounded-xl text-center space-y-6">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">주간 스니펫</h2>
              <p className="text-muted-foreground leading-relaxed">한 주를 돌아보며 핵심 인사이트를 남겨보세요.</p>
              <Button
                size="lg"
                className="w-full text-base px-6 py-5 h-auto shadow-lg hover:shadow-xl transition-all rounded-full"
                onClick={() => router.push('/weekly-snippets')}
              >
                주간 스니펫
              </Button>
            </div>

            <div className="glass-card p-8 md:p-10 rounded-xl text-center space-y-6">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">업적</h2>
              <p className="text-muted-foreground leading-relaxed">획득한 업적을 모아보고 성장 히스토리를 확인해보세요.</p>
              <Button
                size="lg"
                className="w-full text-base px-6 py-5 h-auto shadow-lg hover:shadow-xl transition-all rounded-full"
                onClick={() => router.push('/achievements')}
              >
                업적 보기
              </Button>
            </div>
          </div>

          <section className="glass-card p-6 md:p-8 rounded-xl space-y-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">리더보드</h2>
              <Tabs
                value={state.period}
                onValueChange={(value) => dispatch({ type: 'SET_PERIOD', payload: value as LeaderboardPeriod })}
              >
                <TabsList className="bg-secondary border-[var(--sys-current-border)]">
                  <TabsTrigger
                    value="daily"
                    className="data-[state=active]:bg-[var(--sys-current-bg)] data-[state=active]:text-[var(--sys-current-fg)] data-[state=active]:border-[var(--sys-current-border)]"
                  >
                    일간(어제)
                  </TabsTrigger>
                  <TabsTrigger
                    value="weekly"
                    className="data-[state=active]:bg-[var(--sys-current-bg)] data-[state=active]:text-[var(--sys-current-fg)] data-[state=active]:border-[var(--sys-current-border)]"
                  >
                    주간(지난주)
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            {state.leaderboardLoading ? (
              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <Loader2 className="h-4 w-4 animate-spin text-[var(--sys-spinner-indicator)]" />
                리더보드를 불러오는 중입니다...
              </div>
            ) : state.leaderboardError ? (
              <p className="text-sm text-destructive">{state.leaderboardError}</p>
            ) : state.leaderboard?.excluded_by_league ? (
              <div className="rounded-lg border border-border bg-card/70 p-4">
                <p className="text-sm text-muted-foreground">현재 리그 미참여 상태입니다. 설정에서 리그를 선택하면 랭킹이 표시됩니다.</p>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">
                  기준: {state.leaderboard?.window.key}
                </p>
                <LeaderboardList items={state.leaderboard?.items ?? []} />
              </div>
            )}
          </section>

          <section className="glass-card p-6 md:p-8 rounded-xl space-y-4">
            <div className="flex flex-col gap-2">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">최근 업적</h2>
            </div>

            {state.recentAchievementsLoading ? (
              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <Loader2 className="h-4 w-4 animate-spin text-[var(--sys-spinner-indicator)]" />
                최근 업적 공지를 불러오는 중입니다...
              </div>
            ) : state.recentAchievementsError ? (
              <p className="text-sm text-destructive">{state.recentAchievementsError}</p>
            ) : (
              <RecentAchievementsBoard items={state.recentAchievements} />
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
