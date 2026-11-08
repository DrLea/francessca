"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type LawyerAccount, type LawyerApplication } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AdminShell, fmtDate } from "@/components/AdminShell";
import { Badge, Button, Card, Input, Spinner, Stars, StatusPill } from "@/components/ui";

function ApplicationCard({
  application,
  onDecided,
}: {
  application: LawyerApplication;
  onDecided: () => void;
}) {
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: "approve" | "reject") {
    if (decision === "reject" && !window.confirm(`Reject ${application.name}?`)) return;
    setBusy(decision);
    setError(null);
    try {
      await api.adminDecideApplication(application.id, decision);
      onDecided();
    } catch (err) {
      setError((err as Error).message);
      setBusy(null);
    }
  }

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900">{application.name}</h3>
          <p className="text-sm text-slate-500">
            {[application.law_firm, application.city].filter(Boolean).join(" · ") || "—"}
          </p>
          <p className="mt-1 flex flex-wrap gap-x-4 text-sm">
            <a className="text-brand underline" href={`mailto:${application.email}`}>
              {application.email}
            </a>
            {application.phone && <span className="text-slate-600">{application.phone}</span>}
            {application.website && (
              <a
                className="text-brand underline"
                href={application.website}
                target="_blank"
                rel="noreferrer"
              >
                Website
              </a>
            )}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1 text-xs text-slate-400">
          <StatusPill status={application.status} />
          <span>{fmtDate(application.created_at)}</span>
          <span>{application.user_id ? "Registered account" : "Contact form"}</span>
        </div>
      </div>
      {(application.specializations.length > 0 || application.languages.length > 0) && (
        <div className="mt-3 flex flex-wrap items-center gap-1">
          {application.specializations.map((s) => (
            <Badge key={s}>{s}</Badge>
          ))}
          {application.languages.length > 0 && (
            <span className="ms-1 text-xs text-slate-500">
              Speaks {application.languages.join(", ")}
            </span>
          )}
        </div>
      )}
      {application.message && (
        <p className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
          {application.message}
        </p>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {application.status === "pending" && (
        <div className="mt-4 flex gap-2">
          <Button disabled={busy !== null} onClick={() => decide("approve")}>
            {busy === "approve" ? "Approving…" : "Approve and publish"}
          </Button>
          <Button variant="ghost" disabled={busy !== null} onClick={() => decide("reject")}>
            Reject
          </Button>
        </div>
      )}
    </Card>
  );
}

function AccountRow({
  account,
  onChange,
}: {
  account: LawyerAccount;
  onChange: (account: LawyerAccount) => void;
}) {
  const [extra, setExtra] = useState(String(account.extra_orders));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = Number(extra) !== account.extra_orders;

  async function update(body: { extra_orders?: number; is_published?: boolean }) {
    setBusy(true);
    setError(null);
    try {
      onChange(await api.adminUpdateLawyerAccount(account.id, body));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr className="align-top">
      <td className="py-3 pe-3">
        <div className="font-medium text-slate-900">{account.name}</div>
        <div className="text-xs text-slate-500">
          {[account.email, account.city].filter(Boolean).join(" · ")}
        </div>
        {error && <div className="text-xs text-red-600">{error}</div>}
      </td>
      <td className="py-3 pe-3">
        {account.rating_avg == null ? (
          <span className="text-xs text-slate-400">No reviews</span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-slate-500">
            <Stars value={account.rating_avg} size="text-sm" /> {account.rating_avg.toFixed(1)} (
            {account.rating_count})
          </span>
        )}
      </td>
      <td className="py-3 pe-3 tabular-nums text-slate-700">
        {account.orders_used}
        <span className="text-slate-400"> of {account.free_total + account.extra_orders}</span>
        {account.orders_remaining === 0 && (
          <div className="text-xs font-medium text-amber-700">Allowance used up</div>
        )}
      </td>
      <td className="py-3 pe-3">
        <div className="flex items-center gap-2">
          <Input
            type="number"
            min={0}
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            className="w-20"
            aria-label={`Extra orders for ${account.name}`}
          />
          {dirty && (
            <Button
              disabled={busy || !Number.isInteger(Number(extra)) || Number(extra) < 0}
              onClick={() => update({ extra_orders: Number(extra) })}
            >
              Save
            </Button>
          )}
        </div>
      </td>
      <td className="py-3 text-end">
        <button
          disabled={busy}
          onClick={() => update({ is_published: !account.is_published })}
          className="text-xs font-medium text-slate-500 underline hover:text-slate-800"
        >
          {account.is_published ? "Listed — hide" : "Hidden — publish"}
        </button>
      </td>
    </tr>
  );
}

export default function AdminLawyersPage() {
  const { user } = useAuth();
  const [applications, setApplications] = useState<LawyerApplication[] | null>(null);
  const [accounts, setAccounts] = useState<LawyerAccount[]>([]);
  const [showDecided, setShowDecided] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([api.adminApplications(), api.adminLawyerAccounts()])
      .then(([apps, accs]) => {
        setApplications(apps);
        setAccounts(accs);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (user?.role === "admin") load();
  }, [user, load]);

  const pending = applications?.filter((a) => a.status === "pending") ?? [];
  const decided = applications?.filter((a) => a.status !== "pending") ?? [];

  return (
    <AdminShell
      title="Lawyers"
      lead="Approve new lawyers before they appear in the directory, and manage their order allowance."
      badges={{ "/admin/lawyers": pending.length }}
    >
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!applications && !error && <Spinner label="Loading…" />}

      {applications && (
        <>
          <section className="flex flex-col gap-3">
            <h2 className="font-semibold text-slate-900">
              Waiting for approval{pending.length > 0 ? ` (${pending.length})` : ""}
            </h2>
            {pending.map((a) => (
              <ApplicationCard key={a.id} application={a} onDecided={load} />
            ))}
            {pending.length === 0 && (
              <Card className="text-sm text-slate-500">Nobody is waiting. You are all caught up.</Card>
            )}
          </section>

          <section>
            <h2 className="mb-1 font-semibold text-slate-900">Registered lawyers</h2>
            <p className="mb-3 text-sm text-slate-500">
              Every lawyer gets {accounts[0]?.free_total ?? 3} free orders. Once they are used
              up the lawyer is asked to contact you — add extra orders here to let them continue.
            </p>
            <Card className="p-0">
              {accounts.length === 0 ? (
                <p className="p-6 text-sm text-slate-500">No lawyer has registered yet.</p>
              ) : (
                <div className="overflow-x-auto px-5">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-slate-400">
                        <th className="py-3 pe-3 text-start font-medium">Lawyer</th>
                        <th className="py-3 pe-3 text-start font-medium">Rating</th>
                        <th className="py-3 pe-3 text-start font-medium">Orders used</th>
                        <th className="py-3 pe-3 text-start font-medium">Extra orders</th>
                        <th className="py-3 text-end font-medium">Directory</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {accounts.map((account) => (
                        <AccountRow
                          key={account.id}
                          account={account}
                          onChange={(updated) =>
                            setAccounts((list) =>
                              list.map((a) => (a.id === updated.id ? updated : a)),
                            )
                          }
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </section>

          {decided.length > 0 && (
            <section className="flex flex-col gap-3">
              <button
                className="self-start text-sm font-medium text-slate-500 underline"
                onClick={() => setShowDecided((v) => !v)}
              >
                {showDecided ? "Hide" : "Show"} {decided.length} past decision
                {decided.length === 1 ? "" : "s"}
              </button>
              {showDecided &&
                decided.map((a) => <ApplicationCard key={a.id} application={a} onDecided={load} />)}
            </section>
          )}
        </>
      )}
    </AdminShell>
  );
}
