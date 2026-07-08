"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type DashboardData } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Card, ProgressBar, Spinner } from "@/components/ui";
import type { TranslationKey } from "@/lib/translations";

const TILES: { key: keyof DashboardData; labelKey: TranslationKey; href: string }[] = [
  { key: "conversations", labelKey: "dashboard.tileConversations", href: "/chat" },
  { key: "documents", labelKey: "dashboard.tileDocuments", href: "/files" },
  { key: "timeline_events", labelKey: "dashboard.tileTimelineEvents", href: "/timeline" },
  { key: "cases", labelKey: "dashboard.tileCases", href: "/chat" },
  { key: "exports", labelKey: "dashboard.tileExports", href: "/chat" },
];

export default function DashboardPage() {
  const { user, loading } = useRequireAuth();
  const { t, locale } = useI18n();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api.dashboard().then(setData).catch((e) => setError(e.message));
  }, [user]);

  if (loading || !user)
    return <Centered>{loading && <Spinner label={t("common.loading")} />}</Centered>;

  const limit = data?.token_limit ?? null;
  const used = data?.tokens_used ?? user.tokens_used;

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-slate-900">
        {user.full_name ? t("dashboard.welcomeName", { name: user.full_name }) : t("dashboard.welcome")}
      </h1>
      <p className="mb-6 text-sm text-slate-500">{user.email}</p>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {TILES.map((tile) => (
          <Link key={tile.key} href={tile.href}>
            <Card className="text-center transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg">
              <div className="text-3xl font-bold text-brand">
                {data ? data[tile.key] : "—"}
              </div>
              <div className="text-sm text-slate-500">{t(tile.labelKey)}</div>
            </Card>
          </Link>
        ))}
      </div>

      <Card className="mt-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">{t("dashboard.tokenUsage")}</h2>
          <span className="text-sm text-slate-500">
            {limit !== null
              ? t("dashboard.tokenUsageLimited", {
                  used: used.toLocaleString(locale),
                  limit: limit.toLocaleString(locale),
                })
              : t("dashboard.tokenUsageUnlimited", { used: used.toLocaleString(locale) })}
          </span>
        </div>
        {limit !== null ? (
          <ProgressBar value={used} max={limit} />
        ) : (
          <p className="text-sm text-slate-500">{t("dashboard.premiumPlan")}</p>
        )}
      </Card>
    </main>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-[40vh] items-center justify-center">{children}</div>;
}
