import type { AchievementRarity } from '@/lib/types/auth';

export const rarityLabelMap: Record<AchievementRarity, string> = {
  legend: '레전드',
  epic: '에픽',
  rare: '레어',
  uncommon: '고급',
  common: '일반',
};

export const rarityBadgeClassMap: Record<AchievementRarity, string> = {
  legend: 'bg-primary/20 text-primary',
  epic: 'bg-accent/30 text-accent-700',
  rare: 'bg-secondary text-secondary-foreground',
  uncommon: 'bg-muted text-foreground',
  common: 'bg-card text-muted-foreground border border-border',
};

export const achievementCardClass = 'rounded-xl bg-card/70 p-3.5 md:p-4';
export const achievementAvatarFrameClass = 'bg-muted/80 p-1';
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

export const resolveRecentAchievementRarity = ({ rarity }: { rarity?: string }): AchievementRarity =>
  normalizeRarity(rarity);
