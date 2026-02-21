export function toDateKey(date: Date): string {
  return date.toISOString().split('T')[0];
}

export function getWeekStartDateKey(date: Date): string {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  return toDateKey(d);
}

