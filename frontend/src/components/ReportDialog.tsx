"use client";

import { useState } from "react";
import { api, type ReportReason } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { TranslationKey } from "@/lib/translations";
import { Button, Field, Modal, Select, Textarea } from "@/components/ui";

const REASONS: ReportReason[] = ["not_a_lawyer", "misconduct", "no_response", "privacy", "other"];

/** Report a lawyer. Enough reports from different people suspend the
 *  lawyer at once; an admin reviews every report. */
export function ReportDialog({
  lawyer,
  orderId,
  onClose,
}: {
  lawyer: { id: number; name: string };
  orderId?: number;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [reason, setReason] = useState<ReportReason>("misconduct");
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.reportLawyer({
        lawyer_id: lawyer.id,
        order_id: orderId,
        reason,
        details: details.trim() || undefined,
      });
      setSent(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={t("report.title", { name: lawyer.name })} onClose={onClose}>
      {sent ? (
        <div className="flex flex-col items-start gap-4">
          <p className="text-sm text-green-700">{t("report.sent")}</p>
          <Button variant="ghost" onClick={onClose}>
            {t("lp.close")}
          </Button>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <Field label={t("report.reason")}>
            <Select value={reason} onChange={(e) => setReason(e.target.value as ReportReason)}>
              {REASONS.map((r) => (
                <option key={r} value={r}>
                  {t(`report.reason.${r}` as TranslationKey)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t("report.details")}>
            <Textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              maxLength={4000}
              className="min-h-[96px]"
            />
          </Field>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={busy}>
              {t("report.send")}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              {t("common.cancel")}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
