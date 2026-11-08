"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type LawyerAccount, type LawyerReport } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AdminShell, fmtDate } from "@/components/AdminShell";
import { Button, Card, Input, Spinner, StatusPill } from "@/components/ui";

const REASON: Record<LawyerReport["reason"], string> = {
  not_a_lawyer: "Doubts this is a real lawyer",
  misconduct: "Unprofessional or abusive",
  no_response: "Accepted, never answered",
  privacy: "Misused data",
  other: "Other",
};

/** User reports about lawyers. Enough open reports from different people
 *  suspend a lawyer automatically; this is where an admin decides. */
export default function AdminReportsPage() {
  const { user } = useAuth();
  const [reports, setReports] = useState<LawyerReport[] | null>(null);
  const [lawyers, setLawyers] = useState<Record<number, LawyerAccount>>({});
  const [filter, setFilter] = useState<LawyerReport["status"] | "">("open");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([api.adminReports(filter || undefined), api.adminLawyerAccounts()])
      .then(([r, accounts]) => {
        setReports(r);
        setLawyers(Object.fromEntries(accounts.map((a) => [a.id, a])));
      })
      .catch((e) => setError(e.message));
  }, [filter]);

  useEffect(() => {
    if (user?.role === "admin") load();
  }, [user, load]);

  async function decide(report: LawyerReport, status: LawyerReport["status"], note: string) {
    try {
      await api.adminUpdateReport(report.id, { status, admin_note: note || undefined });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function suspend(lawyerId: number, suspended: boolean) {
    try {
      await api.adminUpdateLawyerAccount(lawyerId, {
        suspended,
        suspension_reason: suspended ? "Suspended after user reports" : undefined,
      });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const open = reports?.filter((r) => r.status === "open").length ?? 0;

  return (
    <AdminShell
      title="Reports"
      lead="What users reported about lawyers. Suspend at once when it is serious; a suspended lawyer is hidden and cannot receive cases."
      badges={{ "/admin/reports": filter === "open" ? open : 0 }}
    >
      <div className="flex gap-2 text-sm">
        {(["open", "resolved", "dismissed", ""] as const).map((f) => (
          <button
            key={f || "all"}
            onClick={() => setFilter(f)}
            className={
              "rounded-lg px-3 py-1 " +
              (filter === f ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-100")
            }
          >
            {f || "all"}
          </button>
        ))}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!reports && !error && <Spinner label="Loading…" />}
      {reports?.length === 0 && <Card className="text-sm text-slate-500">No reports.</Card>}
      {reports?.map((r) => (
        <ReportCard
          key={r.id}
          report={r}
          lawyer={lawyers[r.lawyer_id]}
          onDecide={decide}
          onSuspend={suspend}
        />
      ))}
    </AdminShell>
  );
}

function ReportCard({
  report,
  lawyer,
  onDecide,
  onSuspend,
}: {
  report: LawyerReport;
  lawyer?: LawyerAccount;
  onDecide: (r: LawyerReport, s: LawyerReport["status"], note: string) => void;
  onSuspend: (lawyerId: number, suspended: boolean) => void;
}) {
  const [note, setNote] = useState(report.admin_note ?? "");
  const suspended = lawyer?.verification.is_suspended ?? false;
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900">
            {lawyer?.name ?? `Lawyer #${report.lawyer_id}`}
            {suspended && <span className="ms-2 text-xs font-medium text-red-700">suspended</span>}
          </h3>
          <p className="text-sm text-slate-600">{REASON[report.reason]}</p>
          {report.order_id && <p className="text-xs text-slate-400">Order #{report.order_id}</p>}
        </div>
        <div className="flex flex-col items-end gap-1 text-xs text-slate-400">
          <StatusPill status={report.status} />
          {fmtDate(report.created_at)}
        </div>
      </div>
      {report.details && (
        <p className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
          {report.details}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Internal note"
          className="max-w-xs"
        />
        <Button onClick={() => onDecide(report, "resolved", note)}>Resolved</Button>
        <Button variant="ghost" onClick={() => onDecide(report, "dismissed", note)}>
          Dismiss
        </Button>
        <Button
          variant="ghost"
          className={suspended ? "" : "text-red-600"}
          onClick={() => onSuspend(report.lawyer_id, !suspended)}
        >
          {suspended ? "Lift suspension" : "Suspend lawyer"}
        </Button>
      </div>
    </Card>
  );
}
