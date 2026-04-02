"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { LeagueType } from "@/lib/types/auth";

export const LEAGUE_OPTIONS: Array<{ value: LeagueType; label: string; description: string }> = [
  { value: "undergrad", label: "학부제", description: "학부제 리그에 참여합니다." },
  { value: "semester", label: "학기제", description: "학기제 리그에 참여합니다." },
  { value: "none", label: "미참여", description: "리더보드 집계에서 제외됩니다." },
];

interface LeagueSelectorProps {
  selectedLeague: LeagueType;
  onSelect: (league: LeagueType) => void;
  disabled?: boolean;
}

export function LeagueSelector({ selectedLeague, onSelect, disabled }: LeagueSelectorProps) {
  return (
    <div className="grid gap-2">
      {LEAGUE_OPTIONS.map((option) => {
        const active = selectedLeague === option.value;
        return (
          <Button
            key={option.value}
            type="button"
            variant="outline"
            onClick={() => onSelect(option.value)}
            aria-pressed={active}
            disabled={disabled}
            className={cn(
              "h-auto justify-start rounded-lg px-4 py-3 text-left transition-colors",
              active
                ? "border-[var(--sys-selected-border)] bg-[var(--sys-selected-bg)] text-[var(--sys-selected-fg)] shadow-sm"
                : "border-border bg-card hover:bg-muted/50"
            )}
          >
            <div>
              <p className="text-sm font-semibold text-foreground">{option.label}</p>
              <p className="text-xs text-muted-foreground">{option.description}</p>
            </div>
          </Button>
        );
      })}
    </div>
  );
}
