"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type AdminOverview } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AdminShell, fmtDate, fmtMoney } from "@/components/AdminShell";
import { Card, QualityMeter, Spinner, Stat, StatusPill } from "@/components/ui";

const FUNNEL: { key: "pending" | "accepted" | "closed_won" | "closed_lost" | "declined" | "cancelled"; label: string; tone: string }[] = [
  { key: "pending", label: "Waiting for the lawyer", tone: "bg-amber-400" },
  { key: "accepted", label: "Accepted, in progress", tone: "bg-brand-300" },
  { key: "closed_won", label: "Closed — deal", tone: "bg-green-500" },
  { key: "closed_lost", label: "Closed — no deal", tone: "bg-slate-400" },
  { key: "declined", label: "Declined", tone: "bg-slate-300" },
  { key: "cancelled", label: "Withdrawn by client", tone: "bg-slate-200" },
];

export default function AdminOverviewPage() {
  const { user } = useAuth();
  const [data, setData] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== "admin") return;
    api
      .adminOverview()
      .then(setData)
      .catch((e) => setError(e.message));
  }, [user]);

  const max = data ? Math.max(1, ...FUNNEL.map((f) => data.orders[f.key])) : 1;

  return (
    <AdminShell
      title="Overview"
      lead="Everything in one place: who signed up, what was sent, how it ended."
      badges={{
        "/admin/lawyers": data?.lawyers.pending_approval ?? 0,
        "/admin/feedback": data?.feedback.new ?? 0,
      }}
    >
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!data && !error && <Spinner label="Loading…" />}
      {data && (
        <>
          {(data.lawyers.pending_approval > 0 || data.feedback.new > 0) && (
            <div className="flex flex-wrap gap-3">
              {data.lawyers.pending_approval > 0 && (
                <Link
                  href="/admin/lawyers"
                  className="rounded-xl bg-amber-50 px-4 py-2.5 text-sm font-medium text-amber-800 hover:bg-amber-100"
                >
                  {data.lawyers.pending_approval} lawyer
                  {data.lawyers.pending_approval === 1 ? "" : "s"} waiting for approval →
                </Link>
              )}
              {data.feedback.new > 0 && (
                <Link
                  href="/admin/feedback"
                  className="rounded-xl bg-amber-50 px-4 py-2.5 text-sm font-medium text-amber-800 hover:bg-amber-100"
                >
                  {data.feedback.new} new feedback comment{data.feedback.new === 1 ? "" : "s"} →
                </Link>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat value={data.users.clients} label="Clients" />
            <Stat
              value={data.users.lawyers}
              label="Lawyer accounts"
              hint={`${data.lawyers.live} live · ${data.lawyers.pending_approval} pending`}
            />
            <Stat
              value={data.lawyers.directory}
              label="Directory entries"
              hint="Registered lawyers plus imported ones"
            />
            <Stat
              value={data.orders.total}
              label="Cases sent to lawyers"
              hint={`${data.orders.accepted_total} accepted`}
            />
            <Stat
              value={data.orders.closed_won}
              label="Closed deals"
              hint={`${data.orders.closed_lost} closed without a deal`}
            />
            <Stat
              value={fmtMoney(data.orders.reported_revenue)}
              label="Deal value"
              hint="As reported by lawyers"
            />
            <Stat
              value={data.orders.avg_quality ?? "—"}
              label="Avg. lead quality"
              hint="Automatic score, 0–100"
            />
            <Stat
              value={data.reviews.average ?? "—"}
              label="Avg. lawyer rating"
              hint={`${data.reviews.total} client review${data.reviews.total === 1 ? "" : "s"}`}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <h2 className="mb-4 font-semibold text-slate-900">Orders by status</h2>
              <div className="flex flex-col gap-2.5">
                {FUNNEL.map((f) => (
                  <div key={f.key} className="grid grid-cols-[11rem_1fr_2rem] items-center gap-3 text-sm">
                    <span className="text-slate-600">{f.label}</span>
                    <span className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <span
                        className={`block h-full rounded-full ${f.tone}`}
                        style={{ width: `${(data.orders[f.key] / max) * 100}%` }}
                      />
                    </span>
                    <span className="text-end tabular-nums text-slate-800">
                      {data.orders[f.key]}
                    </span>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <h2 className="mb-4 font-semibold text-slate-900">Assistant activity</h2>
              <dl className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <dt className="text-slate-500">Conversations</dt>
                  <dd className="text-xl font-bold text-slate-900">
                    {data.activity.conversations}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Case summaries</dt>
                  <dd className="text-xl font-bold text-slate-900">{data.activity.cases}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Tokens used</dt>
                  <dd className="text-xl font-bold text-slate-900">
                    {data.activity.tokens.toLocaleString("en-GB")}
                  </dd>
                </div>
              </dl>
              <h3 className="mb-2 mt-6 text-sm font-semibold text-slate-900">Newest accounts</h3>
              <ul className="flex flex-col divide-y divide-slate-100 text-sm">
                {data.recent_users.map((u) => (
                  <li key={u.id} className="flex items-center justify-between gap-3 py-1.5">
                    <span className="min-w-0 truncate text-slate-700">
                      {u.full_name ? `${u.full_name} · ` : ""}
                      <span className="text-slate-500">{u.email}</span>
                    </span>
                    <span className="flex shrink-0 items-center gap-2 text-xs text-slate-400">
                      <StatusPill
                        status={u.role === "lawyer" ? "accepted" : "declined"}
                        label={u.role === "user" ? "client" : u.role}
                      />
                      {fmtDate(u.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card>
            <h2 className="mb-3 font-semibold text-slate-900">Latest orders</h2>
            {data.recent_orders.length === 0 ? (
              <p className="text-sm text-slate-500">
                No client has sent a case to a lawyer yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-start text-xs text-slate-400">
                      <th className="pb-2 pe-3 text-start font-medium">Date</th>
                      <th className="pb-2 pe-3 text-start font-medium">Client → Lawyer</th>
                      <th className="pb-2 pe-3 text-start font-medium">Case</th>
                      <th className="pb-2 pe-3 text-start font-medium">Quality</th>
                      <th className="pb-2 pe-3 text-start font-medium">Status</th>
                      <th className="pb-2 text-end font-medium">Deal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.recent_orders.map((o) => (
                      <tr key={o.id}>
                        <td className="whitespace-nowrap py-2 pe-3 text-slate-500">
                          {fmtDate(o.created_at)}
                        </td>
                        <td className="py-2 pe-3 text-slate-700">
                          {o.client ?? "—"} → {o.lawyer ?? "—"}
                        </td>
                        <td className="py-2 pe-3 text-slate-700">
                          {o.case_title ?? "Message only"}
                        </td>
                        <td className="py-2 pe-3">
                          <QualityMeter score={o.quality_score} />
                        </td>
                        <td className="py-2 pe-3">
                          <StatusPill status={o.status} />
                        </td>
                        <td className="py-2 text-end tabular-nums text-slate-800">
                          {o.deal_value == null ? "—" : fmtMoney(o.deal_value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </AdminShell>
  );
}
