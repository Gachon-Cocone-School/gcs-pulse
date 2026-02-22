'use client';

import React, { useEffect, useState } from 'react';
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
} from '@/lib/types/auth';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface Term {
  id: number;
  is_required: boolean;
}

function LeaderboardList({ items }: { items: LeaderboardItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">표시할 랭킹 데이터가 없습니다.</p>;
  }

  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={`${item.participant_type}-${item.participant_id}`} className="rounded-lg border border-slate-200 bg-white/80 px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-slate-900">
                #{item.rank} {item.participant_name}
              </p>
              <p className="text-xs text-slate-500">
                {item.participant_type === 'team' ? '팀' : '개인'}
                {item.participant_type === 'team' && item.member_count != null ? ` · ${item.member_count}명` : ''}
                {item.participant_type === 'team' && item.submitted_count != null ? ` · 제출 ${item.submitted_count}명` : ''}
              </p>
            </div>
            <p className="text-sm font-bold text-rose-600">{item.score.toFixed(2)}점</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function RecentAchievementsBoard({ items }: { items: RecentAchievementGrantItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">최근 공개 가능한 업적 지급 내역이 없습니다.</p>;
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.grant_id} className="rounded-lg border border-slate-200 bg-white/80 px-4 py-3">
          <div className="flex items-start gap-3">
            <Avatar className="h-12 w-12 rounded-md border border-slate-200 bg-white shrink-0">
              <AvatarImage src={item.badge_image_url} alt={item.achievement_name} className="object-cover" />
              <AvatarFallback className="rounded-md bg-muted">
                <UserIcon className="h-4 w-4 text-muted-foreground" />
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-900">
                {item.user_name} · {item.achievement_name}
              </p>
              <p className="text-xs text-slate-600 mt-1">{item.achievement_description}</p>
              <p className="text-xs text-slate-500 mt-2">획득 시각: {new Date(item.granted_at).toLocaleString('ko-KR')}</p>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function HomePageClient() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [checkingConsents, setCheckingConsents] = useState(true);
  const [mustAgreeTerms, setMustAgreeTerms] = useState(false);
  const [period, setPeriod] = useState<LeaderboardPeriod>('daily');
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null);
  const [leaderboardLoading, setLeaderboardLoading] = useState(false);
  const [leaderboardError, setLeaderboardError] = useState<string | null>(null);
  const [recentAchievements, setRecentAchievements] = useState<RecentAchievementGrantItem[]>([]);
  const [recentAchievementsLoading, setRecentAchievementsLoading] = useState(false);
  const [recentAchievementsError, setRecentAchievementsError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const verifyConsents = async () => {
      try {
        if (isAuthenticated && user) {
          // Fetch all terms to see which ones are required
          const terms = await api.get<Term[]>('/terms');
          const requiredTermIds = terms.filter(t => t.is_required).map(t => t.id);

          // Check if user has agreed to all required terms
          const agreedTermIds = user.consents.map(c => c.term_id);
          const allAgreed = requiredTermIds.every(id => agreedTermIds.includes(id));

          setMustAgreeTerms(!allAgreed);
        }
      } catch (error) {
        console.error('Failed to verify consents:', error);
      } finally {
        setCheckingConsents(false);
      }
    };

    if (!isLoading) {
      verifyConsents();
    }
  }, [isAuthenticated, user, isLoading, router]);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      if (!isAuthenticated) return;
      setLeaderboardLoading(true);
      setLeaderboardError(null);
      try {
        const data = await api.get<LeaderboardResponse>(`/leaderboards?period=${period}`);
        setLeaderboard(data);
      } catch (error: unknown) {
        console.error('Failed to fetch leaderboard:', error);
        setLeaderboardError('리더보드를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
      } finally {
        setLeaderboardLoading(false);
      }
    };

    fetchLeaderboard();
  }, [isAuthenticated, period]);

  useEffect(() => {
    const fetchRecentAchievements = async () => {
      if (!isAuthenticated) return;
      setRecentAchievementsLoading(true);
      setRecentAchievementsError(null);
      try {
        const data = await api.get<RecentAchievementGrantsResponse>('/achievements/recent?limit=10');
        setRecentAchievements(data.items ?? []);
      } catch (error: unknown) {
        console.error('Failed to fetch recent achievements:', error);
        if (error instanceof ApiError && error.status === 404) {
          setRecentAchievements([]);
          setRecentAchievementsError(null);
        } else {
          setRecentAchievementsError('최근 업적 공지를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
        }
      } finally {
        setRecentAchievementsLoading(false);
      }
    };

    fetchRecentAchievements();
  }, [isAuthenticated]);

  // 1. 로딩 중
  if (isLoading || (isAuthenticated && checkingConsents)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-rose-500 animate-spin" />
          <p className="text-slate-500 font-medium">유저 정보를 확인 중입니다...</p>
        </div>
      </div>
    );
  }

  // 2. 미인증 사용자 -> 로그인 페이지 표시
  if (!isAuthenticated) {
    return <LoginPageClient />;
  }

  // 3. 약관 동의 필요 사용자
  if (mustAgreeTerms) {
    redirect('/terms');
  }

  // 4. 권한 체크 -> 역할이 없는 경우 접근 불가 표시
  // (프로젝트 설정에 따라 role 체크 로직은 변경 가능합니다)
  const hasAccess = user?.roles && user.roles.length > 0;

  if (!hasAccess) {
    return <AccessDeniedView />;
  }

  // 5. 모든 조건 통과 -> 메인 대시보드 표시 (Minimal Hero)
  return (
    <div className="min-h-screen bg-slate-50 bg-mesh">
      <Navigation />
      <main className="flex flex-col items-center justify-center p-4 md:py-10">
        <div className="w-full max-w-5xl space-y-8 animate-entrance">
          <div className="text-center space-y-4 glass-card p-8 md:p-10 rounded-xl">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900">
              <span className="premium-gradient-text">GCS Snippets</span>
            </h1>
            <p className="text-xl text-slate-600 leading-relaxed">
              작은 기록이 모여
              <span className="font-semibold text-slate-800"> 특별한 성장</span>을 만듭니다.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-card p-8 md:p-10 rounded-xl text-center space-y-6">
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">일간 스니펫</h2>
              <p className="text-slate-600 leading-relaxed">하루를 정리하며 꾸준한 성장을 기록해보세요.</p>
              <Button
                size="lg"
                className="w-full text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all rounded-full bg-rose-500 hover:bg-rose-600 text-white"
                onClick={() => router.push('/daily-snippets')}
              >
                일간 스니펫
              </Button>
            </div>

            <div className="glass-card p-8 md:p-10 rounded-xl text-center space-y-6">
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">주간 스니펫</h2>
              <p className="text-slate-600 leading-relaxed">한 주를 돌아보며 핵심 인사이트를 남겨보세요.</p>
              <Button
                size="lg"
                className="w-full text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all rounded-full bg-rose-500 hover:bg-rose-600 text-white"
                onClick={() => router.push('/weekly-snippets')}
              >
                주간 스니펫
              </Button>
            </div>

            <div className="glass-card p-8 md:p-10 rounded-xl text-center space-y-6">
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">업적</h2>
              <p className="text-slate-600 leading-relaxed">획득한 업적을 모아보고 성장 히스토리를 확인해보세요.</p>
              <Button
                size="lg"
                className="w-full text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all rounded-full bg-rose-500 hover:bg-rose-600 text-white"
                onClick={() => router.push('/achievements')}
              >
                업적 보기
              </Button>
            </div>
          </div>

          <section className="glass-card p-6 md:p-8 rounded-xl space-y-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">리더보드</h2>
              <Tabs value={period} onValueChange={(value) => setPeriod(value as LeaderboardPeriod)}>
                <TabsList>
                  <TabsTrigger value="daily">일간(어제)</TabsTrigger>
                  <TabsTrigger value="weekly">주간(지난주)</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            {leaderboardLoading ? (
              <div className="flex items-center gap-2 text-slate-500 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                리더보드를 불러오는 중입니다...
              </div>
            ) : leaderboardError ? (
              <p className="text-sm text-rose-600">{leaderboardError}</p>
            ) : leaderboard?.excluded_by_league ? (
              <div className="rounded-lg border border-slate-200 bg-white/70 p-4">
                <p className="text-sm text-slate-600">현재 리그 미참여 상태입니다. 설정에서 리그를 선택하면 랭킹이 표시됩니다.</p>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-slate-500">
                  기준 구간: {leaderboard?.window.label === 'yesterday' ? '어제' : '지난주'} ({leaderboard?.window.key})
                </p>
                <LeaderboardList items={leaderboard?.items ?? []} />
              </div>
            )}
          </section>

          <section className="glass-card p-6 md:p-8 rounded-xl space-y-4">
            <div className="flex flex-col gap-2">
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">최근 업적 공지</h2>
              <p className="text-sm text-slate-500">공개 가능한 업적 지급 이벤트를 최신순으로 보여줍니다.</p>
            </div>

            {recentAchievementsLoading ? (
              <div className="flex items-center gap-2 text-slate-500 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                최근 업적 공지를 불러오는 중입니다...
              </div>
            ) : recentAchievementsError ? (
              <p className="text-sm text-rose-600">{recentAchievementsError}</p>
            ) : (
              <RecentAchievementsBoard items={recentAchievements} />
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
