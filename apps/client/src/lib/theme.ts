export const APP_THEMES = [
  {
    value: "gcs",
    label: "GCS",
    description: "기본 GCS 테마",
  },
  {
    value: "retro",
    label: "Retro",
    description: "복고풍 대비를 강화한 테마",
  },
  {
    value: "matcha-cream",
    label: "Matcha Cream",
    description: "봄 분위기의 차분한 업무용 테마",
  },
  {
    value: "strawberry-choco",
    label: "Strawberry Choco",
    description: "딸기와 초콜릿 대비를 살린 포근한 테마",
  },
] as const;

export type AppTheme = (typeof APP_THEMES)[number]["value"];

export const APP_THEME_VALUES: readonly AppTheme[] = APP_THEMES.map((theme) => theme.value);

export function isAppTheme(value: string | null | undefined): value is AppTheme {
  return APP_THEME_VALUES.some((theme) => theme === value);
}
