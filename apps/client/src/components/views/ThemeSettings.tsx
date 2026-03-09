"use client";

import { useEffect, useMemo } from "react";
import { useTheme } from "next-themes";

import { APP_THEMES, isAppTheme, type AppTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

export function ThemeSettings() {
  const { theme, setTheme } = useTheme();

  const selectedTheme = useMemo<AppTheme>(() => {
    if (isAppTheme(theme)) return theme;
    return "gcs";
  }, [theme]);

  useEffect(() => {
    if (!isAppTheme(theme)) {
      setTheme("gcs");
    }
  }, [setTheme, theme]);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">테마 설정</h2>
        <p className="text-muted-foreground">원하는 테마를 선택하면 즉시 적용됩니다.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {APP_THEMES.map((option) => {
          const active = selectedTheme === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => setTheme(option.value)}
              aria-pressed={active}
              className={cn(
                "rounded-lg border px-4 py-3 text-left transition-colors",
                active
                  ? "border-[var(--sys-selected-border)] bg-[var(--sys-selected-bg)] text-[var(--sys-selected-fg)] shadow-sm"
                  : "border-border bg-card hover:bg-muted/50"
              )}
            >
              <p className="text-sm font-semibold text-foreground">{option.label}</p>
              <p className="text-xs text-muted-foreground">{option.description}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
