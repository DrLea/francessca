"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type TimelineEvent } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Input, Spinner } from "@/components/ui";

function formatDate(iso: string, locale: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Where this entry came from — the document it was read out of, or the
 *  conversation it was mentioned in. Null once that source is deleted. */
function sourceHref(e: TimelineEvent): string | null {
  if (!e.source_label) return null;
  if (e.source_type === "document" && e.source_id) return `/files?doc=${e.source_id}`;
  if (e.conversation_id) return `/chat?c=${e.conversation_id}`;
  return null;
}

export default function TimelinePage() {
  const { user, loading } = useRequireAuth();
  const { t, locale } = useI18n();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);

  // Manual entry — for anything the extractor missed.
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [newDate, setNewDate] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newIsDeadline, setNewIsDeadline] = useState(false);

  useEffect(() => {
    if (!user) return;
    api
      .timeline()
      .then(setEvents)
      .catch((e) => setError(e.message))
      .finally(() => setFetching(false));
  }, [user]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!newDate || !newDescription.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await api.createTimelineEvent({
        event_date: newDate,
        description: newDescription.trim(),
        is_deadline: newIsDeadline,
      });
      setEvents((list) =>
        [...list, created].sort((a, b) => a.event_date.localeCompare(b.event_date)),
      );
      setNewDate("");
      setNewDescription("");
      setNewIsDeadline(false);
      setAdding(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: number) {
    if (!window.confirm(t("timeline.deleteConfirm"))) return;
    setError(null);
    setDeleting(id);
    try {
      await api.deleteTimelineEvent(id);
      setEvents((list) => list.filter((e) => e.id !== id));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDeleting(null);
    }
  }

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

      <div className="mb-4">
        {adding ? (
          <Card>
            <form onSubmit={add} className="flex flex-col gap-3">
              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  type="date"
                  value={newDate}
                  onChange={(ev) => setNewDate(ev.target.value)}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
                  required
                />
                <Input
                  value={newDescription}
                  onChange={(ev) => setNewDescription(ev.target.value)}
                  placeholder={t("timeline.addDescription")}
                  maxLength={2000}
                  required
                />
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={newIsDeadline}
                  onChange={(ev) => setNewIsDeadline(ev.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 accent-[#3b5bdb]"
                />
                {t("timeline.addIsDeadline")}
              </label>
              <div className="flex items-center gap-2">
                <Button type="submit" disabled={saving || !newDate || !newDescription.trim()}>
                  {saving ? t("timeline.saving") : t("timeline.save")}
                </Button>
                <Button type="button" variant="ghost" onClick={() => setAdding(false)}>
                  {t("timeline.cancel")}
                </Button>
              </div>
            </form>
          </Card>
        ) : (
          <Button variant="secondary" onClick={() => setAdding(true)}>
            {t("timeline.addEntry")}
          </Button>
        )}
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {fetching && <Spinner label={t("timeline.loadingTimeline")} />}

      {!fetching && events.length === 0 && (
        <Card>
          <p className="text-sm text-slate-500">{t("timeline.noEvents")}</p>
        </Card>
      )}

      <ol className="relative ms-3 flex flex-col gap-4 border-s-2 border-slate-200 ps-6">
        {events.map((e) => {
          const href = sourceHref(e);
          return (
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
                    {formatDate(e.event_date, locale)}
                  </span>
                  <div className="flex items-center gap-2">
                    {e.is_deadline && (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                        {t("timeline.deadline")}
                      </span>
                    )}
                    <Button
                      variant="ghost"
                      className="!px-2 !py-1 text-xs text-red-600 hover:bg-red-50"
                      disabled={deleting === e.id}
                      onClick={() => remove(e.id)}
                    >
                      {deleting === e.id ? t("timeline.deleting") : t("timeline.delete")}
                    </Button>
                  </div>
                </div>
                <p className="text-sm text-slate-700">{e.description}</p>

                {/* Straight back to the document or conversation it came from. */}
                <div className="mt-2 text-xs">
                  {href ? (
                    <Link
                      href={href}
                      className="inline-flex max-w-full items-center gap-1 truncate rounded-full bg-brand-50 px-2.5 py-0.5 font-medium text-brand-700 transition-colors hover:bg-brand-100"
                      title={t("timeline.openSource")}
                    >
                      <span aria-hidden>{e.source_type === "document" ? "📄" : "💬"}</span>
                      <span className="truncate">{e.source_label}</span>
                    </Link>
                  ) : (
                    <span className="text-slate-400">
                      {e.source_type === "manual"
                        ? t("timeline.addedByYou")
                        : e.source_type === "document"
                          ? t("timeline.fromDocument")
                          : t("timeline.fromChat")}
                    </span>
                  )}
                </div>
              </Card>
            </li>
          );
        })}
      </ol>
    </main>
  );
}
