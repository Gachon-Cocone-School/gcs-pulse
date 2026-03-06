import type { AchievementRarity } from '@/lib/types/auth';

export const rarityLabelMap: Record<AchievementRarity, string> = {
  legend: '레전드',
  epic: '에픽',
  rare: '레어',
  uncommon: '고급',
  common: '일반',
};

export const rarityBadgeClassMap: Record<AchievementRarity, string> = {
  legend: 'bg-red-50 text-red-700',
  epic: 'bg-purple-50 text-purple-700',
  rare: 'bg-blue-50 text-blue-700',
  uncommon: 'bg-green-50 text-green-700',
  common: 'bg-white text-slate-700 border border-slate-300',
};

export const achievementCardClass = 'rounded-xl bg-white/70 p-3.5 md:p-4';
export const achievementAvatarFrameClass = 'bg-slate-100/80 p-1';
export const achievementAvatarImageClass = 'rounded-md object-cover';

export const normalizeRarity = (rarity?: string): AchievementRarity => {
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

export type RecentAchievementRarityLike = {
  rarity?: string;
};

export const resolveRecentAchievementRarity = ({ rarity }: RecentAchievementRarityLike): AchievementRarity =>
  normalizeRarity(rarity);
