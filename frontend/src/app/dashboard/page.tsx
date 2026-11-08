"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type DashboardData, type TimelineEvent } from "@/lib/api";
import { useAuth, useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Spinner } from "@/components/ui";
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

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <UpcomingCard />
        <PrivacyCard />
      </div>
    </main>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-[40vh] items-center justify-center">{children}</div>;
}


/** In-app reminders: dated entries in the next two weeks. */
function UpcomingCard() {
  const { t, locale } = useI18n();
  const [events, setEvents] = useState<TimelineEvent[] | null>(null);

  useEffect(() => {
    api.upcoming(14).then(setEvents).catch(() => setEvents([]));
  }, []);

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const when = (iso: string) => {
    const days = Math.round((new Date(iso + "T00:00:00").getTime() - today.getTime()) / 86_400_000);
    if (days <= 0) return t("upcoming.today");
    if (days === 1) return t("upcoming.tomorrow");
    return t("upcoming.inDays", { count: days });
  };

  return (
    <Card>
      <h2 className="mb-3 font-semibold text-slate-900">{t("upcoming.title")}</h2>
      {events === null ? (
        <Spinner />
      ) : events.length === 0 ? (
        <p className="text-sm text-slate-500">{t("upcoming.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2 text-sm">
          {events.map((e) => (
            <li key={e.id} className="flex items-start justify-between gap-3">
              <span className="text-slate-700">
                {e.is_deadline && <span className="me-1 text-red-600">●</span>}
                {e.description}
              </span>
              <span className="whitespace-nowrap text-xs text-slate-500">
                {e.event_date && new Date(e.event_date).toLocaleDateString(locale)} ·{" "}
                {e.event_date && when(e.event_date)}
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs text-slate-400">{t("upcoming.note")}</p>
      <Link href="/timeline" className="mt-2 inline-block text-sm text-brand underline">
        {t("dashboard.tileTimelineEvents")}
      </Link>
    </Card>
  );
}

/** Slide 12: her data, her rules. Export or delete everything in one tap. */
function PrivacyCard() {
  const { t, locale } = useI18n();
  const { user, signOut } = useAuth();
  const [busy, setBusy] = useState<"export" | "delete" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function exportAll() {
    setBusy("export");
    setError(null);
    try {
      await api.exportMyData();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function deleteAll() {
    if (window.prompt(t("privacy.deleteConfirm")) !== "DELETE") return;
    setBusy("delete");
    setError(null);
    try {
      await api.deleteAccount();
      window.alert(t("privacy.deleted"));
      signOut();
    } catch (err) {
      setError((err as Error).message);
      setBusy(null);
    }
  }

  return (
    <Card>
      <h2 className="mb-1 font-semibold text-slate-900">{t("privacy.title")}</h2>
      <p className="text-sm text-slate-600">{t("privacy.body")}</p>
      <p className="mt-2 text-xs text-slate-500">
        {user?.data_consent_at
          ? t("privacy.consentSince", {
              date: new Date(user.data_consent_at).toLocaleDateString(locale),
            })
          : t("privacy.noConsent")}
      </p>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="secondary" onClick={exportAll} disabled={busy !== null}>
          {t("privacy.export")}
        </Button>
        <Button variant="ghost" onClick={deleteAll} disabled={busy !== null} className="text-red-600">
          {t("privacy.delete")}
        </Button>
      </div>
    </Card>
  );
}
