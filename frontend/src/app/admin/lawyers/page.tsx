"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type AdminLawyerUpdate, type LawyerAccount, type LawyerApplication, type Partner } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AdminShell, fmtDate } from "@/components/AdminShell";
import { Badge, Button, Card, Spinner, Stars, StatusPill } from "@/components/ui";

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

const SUB_TONE: Record<string, string> = {
  trial: "bg-brand-50 text-brand-700",
  active: "bg-green-50 text-green-700",
  expired: "bg-amber-50 text-amber-700",
  not_started: "bg-slate-100 text-slate-500",
};

function Check({ ok, label }: { ok: boolean | null; label: string }) {
  return (
    <span
      className={
        "rounded-full px-2 py-0.5 text-[11px] font-medium " +
        (ok ? "bg-green-50 text-green-700" : ok === null ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-500")
      }
    >
      {ok ? "✓ " : ""}
      {label}
    </span>
  );
}

/** One registered lawyer: subscription, the four verification checks,
 *  suspension and directory visibility. */
function AccountCard({
  account,
  partners,
  onChange,
}: {
  account: LawyerAccount;
  partners: Partner[];
  onChange: (account: LawyerAccount) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [beaCode, setBeaCode] = useState<string | null>(null);
  const sub = account.subscription;
  const v = account.verification;

  async function run(action: () => Promise<LawyerAccount>) {
    setBusy(true);
    setError(null);
    try {
      onChange(await action());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const update = (body: AdminLawyerUpdate) => run(() => api.adminUpdateLawyerAccount(account.id, body));

  async function issueCode() {
    if (v.bea_code_sent && !window.confirm("Issue a new code? The previous one stops working.")) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.adminIssueBeaCode(account.id);
      setBeaCode(res.code);
      onChange(res.lawyer);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const registerUrl = "https://www.rechtsanwaltsregister.org/";

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="flex flex-wrap items-center gap-2 font-semibold text-slate-900">
            {account.name}
            {v.is_verified && <Check ok label="Verified" />}
            {v.is_suspended && (
              <span className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-medium text-red-700">
                Suspended
              </span>
            )}
          </h3>
          <p className="text-xs text-slate-500">
            {[account.law_firm, account.email, account.city].filter(Boolean).join(" · ")}
          </p>
          <p className="mt-1 flex items-center gap-2 text-xs text-slate-500">
            {account.rating_avg == null ? (
              "No reviews"
            ) : (
              <>
                <Stars value={account.rating_avg} size="text-sm" /> {account.rating_avg.toFixed(1)} (
                {account.rating_count})
              </>
            )}
            <span>· {account.orders_accepted} cases accepted</span>
            {account.open_reports > 0 && (
              <span className="font-medium text-red-700">· {account.open_reports} open reports</span>
            )}
          </p>
        </div>
        <button
          disabled={busy}
          onClick={() => update({ is_published: !account.is_published })}
          className="text-xs font-medium text-slate-500 underline hover:text-slate-800"
        >
          {account.is_published ? "Listed — hide" : "Hidden — publish"}
        </button>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {/* Subscription: flat €99/month after the trial, never per client. */}
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-600">
            Subscription
            <span className={"rounded-full px-2 py-0.5 " + (SUB_TONE[sub.state] ?? "")}>{sub.state}</span>
          </div>
          <p className="text-xs text-slate-500">
            Trial ends: {sub.trial_ends_at ? fmtDate(sub.trial_ends_at) : "—"} · Paid until:{" "}
            {sub.paid_until ? fmtDate(sub.paid_until) : "—"}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button disabled={busy} onClick={() => update({ extend_paid_months: 1 })}>
              Record payment: +1 month
            </Button>
            <Button variant="ghost" disabled={busy} onClick={() => update({ extend_paid_months: 12 })}>
              +12 months
            </Button>
          </div>
        </div>

        {/* Verification: register, beA code, ID check, yearly re-check. */}
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="mb-2 text-xs font-medium text-slate-600">Verification</div>
          <p className="text-xs text-slate-500">
            Register: {account.brak_register_id || "—"} · {account.chamber || "—"} · admitted{" "}
            {account.admission_date ? fmtDate(account.admission_date) : "—"}{" "}
            <a className="text-brand underline" href={registerUrl} target="_blank" rel="noreferrer">
              open BRAK register
            </a>
          </p>
          <div className="mt-2 flex flex-wrap gap-1">
            <Check ok={v.register_checked} label="Register" />
            <Check ok={v.bea_verified ? true : v.bea_code_sent ? null : false} label="beA" />
            <Check
              ok={v.id_check_status === "passed" ? true : v.id_check_status === "pending" ? null : false}
              label={`ID: ${v.id_check_status.replace("_", " ")}`}
            />
            {v.verified_until && <Check ok label={`until ${fmtDate(v.verified_until)}`} />}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button
              variant="ghost"
              disabled={busy}
              onClick={() => update({ register_checked: !v.register_checked })}
            >
              {v.register_checked ? "Undo register check" : "Register checked"}
            </Button>
            {!v.bea_verified && (
              <Button variant="ghost" disabled={busy} onClick={issueCode}>
                {v.bea_code_sent ? "New beA code" : "Issue beA code"}
              </Button>
            )}
            <select
              className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs"
              value={v.id_check_status}
              disabled={busy}
              onChange={(e) =>
                update({ id_check_status: e.target.value as AdminLawyerUpdate["id_check_status"] })
              }
              aria-label="ID check"
            >
              <option value="not_started">ID: not started</option>
              <option value="pending">ID: pending</option>
              <option value="passed">ID: passed</option>
              <option value="failed">ID: failed</option>
            </select>
            {v.is_verified && (
              <Button
                variant="ghost"
                disabled={busy}
                onClick={() =>
                  window.confirm("Start the yearly re-check? The badge disappears until all checks pass again.") &&
                  run(() => api.adminStartRecheck(account.id))
                }
              >
                Start re-check
              </Button>
            )}
          </div>
          {beaCode && (
            <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Send this code to the lawyer&apos;s beA mailbox now — it is shown only once:{" "}
              <span className="font-mono font-semibold tracking-widest">{beaCode}</span>
            </p>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {partners.length > 0 && (
          <select
            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs"
            value={account.partner_id ?? ""}
            disabled={busy}
            onChange={(e) =>
              update({ partner_id: e.target.value ? Number(e.target.value) : null })
            }
            aria-label="Partner"
          >
            <option value="">No partner (law firm)</option>
            {partners.map((p) => (
              <option key={p.id} value={p.id}>
                Member of {p.name}
              </option>
            ))}
          </select>
        )}
        {v.is_suspended ? (
          <>
            <span className="text-xs text-red-700">{account.suspension_reason}</span>
            <Button variant="ghost" disabled={busy} onClick={() => update({ suspended: false })}>
              Lift suspension
            </Button>
          </>
        ) : (
          <Button
            variant="ghost"
            className="text-red-600"
            disabled={busy}
            onClick={() => {
              const reason = window.prompt("Reason for the suspension (shown to admins):");
              if (reason !== null) void update({ suspended: true, suspension_reason: reason || undefined });
            }}
          >
            Suspend now
          </Button>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </Card>
  );
}

export default function AdminLawyersPage() {
  const { user } = useAuth();
  const [applications, setApplications] = useState<LawyerApplication[] | null>(null);
  const [accounts, setAccounts] = useState<LawyerAccount[]>([]);
  const [partners, setPartners] = useState<Partner[]>([]);
  const [showDecided, setShowDecided] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([api.adminApplications(), api.adminLawyerAccounts(), api.adminPartners()])
      .then(([apps, accs, parts]) => {
        setApplications(apps);
        setAccounts(accs);
        setPartners(parts);
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
      lead="Approve new lawyers, record subscriptions, run the verification checks, and suspend when needed."
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

          <section className="flex flex-col gap-3">
            <div>
              <h2 className="font-semibold text-slate-900">Registered lawyers</h2>
              <p className="text-sm text-slate-500">
                Approval starts a free trial; after it, firms pay a flat fee per month (never per
                client). Record payments here. A lawyer is verified once the register, the beA code
                and the ID check have passed; verification lasts a year.
              </p>
            </div>
            {accounts.length === 0 && (
              <Card className="text-sm text-slate-500">No lawyer has registered yet.</Card>
            )}
            {accounts.map((account) => (
              <AccountCard
                key={account.id}
                account={account}
                partners={partners}
                onChange={(updated) =>
                  setAccounts((list) => list.map((a) => (a.id === updated.id ? updated : a)))
                }
              />
            ))}
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
