"use client";

import { useEffect, useState } from "react";
import { api, type TimelineEvent } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Badge, Card, Spinner } from "@/components/ui";

function formatDate(e: TimelineEvent, locale: string, undatedLabel: string): string {
  if (e.event_date) {
    return new Date(e.event_date + "T00:00:00").toLocaleDateString(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }
  return e.date_label || undatedLabel;
}

export default function TimelinePage() {
  const { user, loading } = useRequireAuth();
  const { t, locale } = useI18n();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api
      .timeline()
      .then(setEvents)
      .catch((e) => setError(e.message))
      .finally(() => setFetching(false));
  }, [user]);

  if (loading || !user)
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        {loading && <Spinner label={t("common.loading")} />}
      </div>
    );

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-slate-900">{t("timeline.title")}</h1>
      <p className="mb-6 text-sm text-slate-500">{t("timeline.subtitle")}</p>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {fetching && <Spinner label={t("timeline.loadingTimeline")} />}

      {!fetching && events.length === 0 && (
        <Card>
          <p className="text-sm text-slate-500">{t("timeline.noEvents")}</p>
        </Card>
      )}

      <ol className="relative ms-3 flex flex-col gap-4 border-s-2 border-slate-200 ps-6">
        {events.map((e) => (
          <li key={e.id} className="relative">
            <span
              className={
                "absolute -start-[31px] top-1.5 h-3 w-3 rounded-full border-2 border-white " +
                (e.is_deadline ? "bg-red-500" : "bg-brand")
              }
            />
            <Card className="py-3">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-slate-700">
                  {formatDate(e, locale, t("timeline.undated"))}
                </span>
                <div className="flex items-center gap-2">
                  {e.is_deadline && (
                    <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                      {t("timeline.deadline")}
                    </span>
                  )}
                  <Badge>
                    {e.source_type === "document" ? t("timeline.fromDocument") : t("timeline.fromChat")}
                  </Badge>
                </div>
              </div>
              <p className="text-sm text-slate-700">{e.description}</p>
            </Card>
          </li>
        ))}
      </ol>
    </main>
  );
}
