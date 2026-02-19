"use client";

import { TokenManager } from "@/components/views/TokenManager";
import { Separator } from "@/components/ui/separator";
import { Navigation } from "@/components/Navigation";
import { PageHeader } from "@/components/PageHeader";
import { useAuth } from "@/context/auth-context";
import { redirect } from "next/navigation";
import { Loader2 } from "lucide-react";

export default function SettingsPage() {
  const { isAuthenticated, isLoading } = useAuth();

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

        <div className="mt-8 flex flex-col space-y-8 lg:flex-row lg:space-x-12 lg:space-y-0">
          <div className="flex-1">
            <div className="glass-card p-8 rounded-xl animate-entrance">
              <section id="api-access" className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium">API 액세스</h3>
                  <p className="text-sm text-muted-foreground">
                    이 토큰을 사용하여 자체 스크립트나 애플리케이션에서 API를 인증하세요.
                  </p>
                </div>
                <Separator />
                <TokenManager />
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
