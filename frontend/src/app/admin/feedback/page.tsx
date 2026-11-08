"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type AdminFeedback } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AdminShell, fmtDate } from "@/components/AdminShell";
import {
  Button,
  Card,
  QualityMeter,
  Select,
  Spinner,
  Stars,
  Stat,
  StatusPill,
  Textarea,
} from "@/components/ui";

const CATEGORY_LABEL: Record<string, string> = {
  lead_quality: "Lead quality",
  platform: "Platform",
  idea: "Idea",
  bug: "Bug",
  other: "Other",
};

type Summary = Awaited<ReturnType<typeof api.adminFeedback>>["summary"];

function FeedbackCard({
  item,
  onChange,
}: {
  item: AdminFeedback;
  onChange: (item: AdminFeedback) => void;
}) {
  const [note, setNote] = useState(item.admin_note ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const noteDirty = note.trim() !== (item.admin_note ?? "");

  async function update(body: { status?: "new" | "reviewed"; admin_note?: string }) {
    setBusy(true);
    setError(null);
    try {
      onChange(await api.adminUpdateFeedback(item.id, body));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-semibold text-slate-900">{item.lawyer_name}</span>
          {item.lawyer_city && <span className="text-slate-500">{item.lawyer_city}</span>}
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {CATEGORY_LABEL[item.category] ?? item.category}
          </span>
          {item.rating != null && <Stars value={item.rating} size="text-sm" />}
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          {fmtDate(item.created_at)}
          <StatusPill status={item.status} />
        </div>
      </div>

      <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
        {item.comment}
      </p>

      {item.order_id != null && (
        <p className="mt-3 flex flex-wrap items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
          About order #{item.order_id}
          {item.order_case_title ? ` · ${item.order_case_title}` : ""}
          {item.order_quality_score != null && (
            <>
              <span>· automatic score</span>
              <QualityMeter score={item.order_quality_score} />
            </>
          )}
        </p>
      )}

      <div className="mt-3 flex flex-col gap-2">
        <Textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Internal note — what to do about this (not shown to the lawyer)"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-wrap gap-2">
          {noteDirty && (
            <Button disabled={busy} onClick={() => update({ admin_note: note })}>
              Save note
            </Button>
          )}
          <Button
            variant={item.status === "new" ? "secondary" : "ghost"}
            disabled={busy}
            onClick={() => update({ status: item.status === "new" ? "reviewed" : "new" })}
          >
            {item.status === "new" ? "Mark as reviewed" : "Mark as new again"}
          </Button>
        </div>
      </div>
    </Card>
  );
}

export default function AdminFeedbackPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<AdminFeedback[] | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [status, setStatus] = useState<"" | "new" | "reviewed">("new");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .adminFeedback({ status: status || undefined, category: category || undefined })
      .then((res) => {
        setItems(res.items);
        setSummary(res.summary);
      })
      .catch((e) => setError(e.message));
  }, [status, category]);

  useEffect(() => {
    if (user?.role === "admin") load();
  }, [user, load]);

  const lead = summary?.by_category.lead_quality;

  return (
    <AdminShell
      title="Lawyer feedback"
      lead="What lawyers say about the leads they receive and about the platform."
      badges={{ "/admin/feedback": summary?.new ?? 0 }}
    >
      {error && <p className="text-sm text-red-600">{error}</p>}

      {summary && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat value={summary.new} label="New" hint="Not yet reviewed" />
          <Stat value={summary.total} label="Comments in total" />
          <Stat
            value={lead?.avg_rating ?? "—"}
            label="Lead quality rating"
            hint={`Out of 5 · ${lead?.count ?? 0} comment${lead?.count === 1 ? "" : "s"}`}
          />
          <Stat
            value={
              (summary.by_category.bug?.count ?? 0) + (summary.by_category.idea?.count ?? 0)
            }
            label="Bugs and ideas"
          />
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Select
          className="w-auto"
          value={status}
          onChange={(e) => setStatus(e.target.value as typeof status)}
          aria-label="Status"
        >
          <option value="new">New only</option>
          <option value="reviewed">Reviewed</option>
          <option value="">All</option>
        </Select>
        <Select
          className="w-auto"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Category"
        >
          <option value="">Every category</option>
          {Object.entries(CATEGORY_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
              {summary?.by_category[value] ? ` (${summary.by_category[value].count})` : ""}
            </option>
          ))}
        </Select>
      </div>

      {!items && !error && <Spinner label="Loading…" />}
      {items?.map((item) => (
        <FeedbackCard
          key={item.id}
          item={item}
          onChange={(updated) => {
            setItems((list) => (list ?? []).map((i) => (i.id === updated.id ? updated : i)));
            load(); // keeps the counters and the current filter honest
          }}
        />
      ))}
      {items?.length === 0 && (
        <Card className="text-sm text-slate-500">
          {status === "new" ? "No new feedback. You are all caught up." : "Nothing matches this filter."}
        </Card>
      )}
    </AdminShell>
  );
}
