export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="theme-spinner h-12 w-12 rounded-full border-4 animate-spin" />
        <p className="text-muted-foreground font-medium">로딩 중...</p>
      </div>
    </div>
  );
}
