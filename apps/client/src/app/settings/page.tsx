"use client";

import { Suspense, useEffect, useState } from "react";
import { TokenManager } from "@/components/views/TokenManager";
import { TeamManager } from "@/components/views/TeamManager";
import { Navigation } from "@/components/Navigation";
import { PageHeader } from "@/components/PageHeader";
import { useAuth } from "@/context/auth-context";
import { redirect, usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

function SettingsPageContent() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menu, setMenu] = useState<"api" | "team">("api");

  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncMenuFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const nextMenu = params.get("menu") === "team" ? "team" : "api";
      setMenu(nextMenu);
    };

    syncMenuFromUrl();
    window.addEventListener("popstate", syncMenuFromUrl);

    return () => {
      window.removeEventListener("popstate", syncMenuFromUrl);
    };
  }, []);

  const handleMenuChange = (value: "api" | "team") => {
    const params = new URLSearchParams(window.location.search);

    if (value === "team") {
      params.set("menu", "team");
    } else {
      params.delete("menu");
    }

    const queryString = params.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname);
    setMenu(value);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50 bg-mesh">
      <Navigation />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <PageHeader
          title="설정"
          description="계정 설정 및 API 액세스를 관리합니다."
        />

        <div className="mt-8">
          <div className="glass-card p-8 rounded-xl animate-entrance">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-[220px_1fr]">
              <aside className="space-y-2">
                <p className="text-xs font-semibold tracking-wider text-slate-500 uppercase">설정 메뉴</p>
                <button
                  type="button"
                  onClick={() => handleMenuChange("api")}
                  className={cn(
                    "w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                    menu === "api"
                      ? "bg-rose-50 text-rose-700"
                      : "text-slate-700 hover:bg-slate-100"
                  )}
                >
                  API 키
                </button>
                <button
                  type="button"
                  onClick={() => handleMenuChange("team")}
                  className={cn(
                    "w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                    menu === "team"
                      ? "bg-rose-50 text-rose-700"
                      : "text-slate-700 hover:bg-slate-100"
                  )}
                >
                  팀 관리
                </button>
              </aside>

              <section>
                {menu === "api" ? <TokenManager /> : <TeamManager />}
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center items-center min-h-[50vh]">
          <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
        </div>
      }
    >
      <SettingsPageContent />
    </Suspense>
  );
}
