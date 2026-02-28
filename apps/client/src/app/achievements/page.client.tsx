'use client';

import React from 'react';
import { redirect } from 'next/navigation';
import { Loader2, User as UserIcon } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { useAuth } from '@/context/auth-context';
import { api } from '@/lib/api';
import type {
  AchievementRarity,
  MyAchievementGroupItem,
  MyAchievementGroupsResponse,
  UserConsent,
} from '@/lib/types/auth';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import LoginPageClient from '@/app/login/LoginPageClient';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { hasPrivilegedRole } from '@/lib/types';

interface Term {
  id: number;
  is_required: boolean;
}


const rarityLabelMap: Record<AchievementRarity, string> = {
  legend: '레전드',
  epic: '에픽',
  rare: '레어',
  uncommon: '고급',
  common: '일반',
};

const rarityCardClassMap: Record<AchievementRarity, string> = {
  legend: 'border-red-300',
  epic: 'border-purple-300',
  rare: 'border-blue-300',
  uncommon: 'border-green-300',
  common: 'border-white',
};

const rarityBadgeClassMap: Record<AchievementRarity, string> = {
  legend: 'bg-red-50 text-red-700',
  epic: 'bg-purple-50 text-purple-700',
  rare: 'bg-blue-50 text-blue-700',
  uncommon: 'bg-green-50 text-green-700',
  common: 'bg-white text-slate-700 border border-slate-300',
};

const normalizeRarity = (rarity?: string): AchievementRarity => {
  const normalized = rarity?.trim().toLowerCase();

  if (!normalized) return 'common';

  if (normalized === 'legend' || normalized === 'legendary' || normalized === '레전드' || normalized === '전설' || normalized === '5') {
    return 'legend';
  }
  if (normalized === 'epic' || normalized === '에픽' || normalized === '4') {
    return 'epic';
  }
  if (normalized === 'rare' || normalized === '레어' || normalized === '3') {
    return 'rare';
  }
  if (normalized === 'uncommon' || normalized === '고급' || normalized === '언커먼' || normalized === '2') {
    return 'uncommon';
  }
  if (normalized === 'common' || normalized === '일반' || normalized === '커먼' || normalized === '1') {
    return 'common';
  }

  return 'common';
};

function MyAchievementList({ items }: { items: MyAchievementGroupItem[] }) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white/70 p-5">
        <p className="text-sm text-slate-500">아직 획득한 업적이 없습니다.</p>
      </div>
    );
  }

  return (
    <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {items.map((item) => {
        const rarity = normalizeRarity(item.rarity);
        return (
          <li key={item.achievement_definition_id} className={`rounded-xl border bg-white/80 p-4 ${rarityCardClassMap[rarity]}`}>
            <div className="flex items-start gap-3">
              <Avatar className="h-14 w-14 rounded-lg border border-slate-200 bg-white">
                <AvatarImage src={item.badge_image_url} alt={item.name} className="object-cover" />
                <AvatarFallback className="rounded-lg bg-muted">
                  <UserIcon className="h-5 w-5 text-muted-foreground" />
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-base font-semibold text-slate-900">{item.name}</p>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${rarityBadgeClassMap[rarity]}`}>
                    {rarityLabelMap[rarity]}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{item.description}</p>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                  <span className="rounded-full bg-rose-50 px-2 py-1 font-semibold text-rose-700">x{item.grant_count}</span>
                  <span>최근 획득: {new Date(item.last_granted_at).toLocaleString('ko-KR')}</span>
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export default function AchievementsPageClient() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [checkingConsents, setCheckingConsents] = React.useState(true);
  const hasAccess = hasPrivilegedRole(user?.roles);
  const [mustAgreeTerms, setMustAgreeTerms] = React.useState(false);
  const [items, setItems] = React.useState<MyAchievementGroupItem[]>([]);
  const [listLoading, setListLoading] = React.useState(false);
  const [listError, setListError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const verifyConsents = async () => {
      try {
        if (isAuthenticated && user) {
          const terms = await api.get<Term[]>('/terms');
          const requiredTermIds = terms.filter((t) => t.is_required).map((t) => t.id);
          const agreedTermIds = (user.consents as UserConsent[]).map((c) => c.term_id);
          const allAgreed = requiredTermIds.every((id) => agreedTermIds.includes(id));
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
  }, [isAuthenticated, user, isLoading]);

  React.useEffect(() => {
    const fetchMyAchievements = async () => {
      if (!isAuthenticated || !hasAccess) return;
      setListLoading(true);
      setListError(null);
      try {
        const data = await api.get<MyAchievementGroupsResponse>('/achievements/me');
        setItems(data.items ?? []);
      } catch (error) {
        console.error('Failed to fetch my achievements:', error);
        setListError('업적 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
      } finally {
        setListLoading(false);
      }
    };

    fetchMyAchievements();
  }, [isAuthenticated, hasAccess]);

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

  if (!isAuthenticated) {
    return <LoginPageClient />;
  }

  if (!hasAccess) {
    return <AccessDeniedView reason="student-only" />;
  }

  if (mustAgreeTerms) {
    redirect('/terms');
  }

  return (
    <div className="min-h-screen bg-slate-50 bg-mesh">
      <Navigation />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <PageHeader
          title="내 업적"
          description="획득한 업적을 업적별로 모아보고 지급 횟수와 최근 획득 시각을 확인하세요."
        />

        <section className="glass-card p-6 md:p-8 rounded-xl space-y-4">
          {listLoading ? (
            <div className="flex items-center gap-2 text-slate-500 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              업적 정보를 불러오는 중입니다...
            </div>
          ) : listError ? (
            <p className="text-sm text-rose-600">{listError}</p>
          ) : (
            <MyAchievementList items={items} />
          )}
        </section>
      </main>
    </div>
  );
}
