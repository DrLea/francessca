"use client";

import { useState } from "react";
import { api, type LawyerMe, type LawyerSubscription } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Field, Input } from "@/components/ui";

/** One line on the subscription: trial, paid, or expired. */
export function subscriptionLine(
  sub: LawyerSubscription,
  t: ReturnType<typeof useI18n>["t"],
  locale: string,
): string {
  const date = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString(locale) : "");
  switch (sub.state) {
    case "trial":
      return t("lp.sub.trial", { date: date(sub.trial_ends_at) });
    case "active":
      return t("lp.sub.active", { date: date(sub.paid_until) });
    case "expired":
      return t("lp.sub.expired");
    default:
      return t("lp.sub.notStarted");
  }
}

function Step({ label, state }: { label: string; state: "done" | "pending" | "failed" | "todo" }) {
  const { t } = useI18n();
  const tone = {
    done: "bg-green-50 text-green-700",
    pending: "bg-amber-50 text-amber-700",
    failed: "bg-red-50 text-red-700",
    todo: "bg-slate-100 text-slate-500",
  }[state];
  const text = {
    done: t("lp.ver.done"),
    pending: t("lp.ver.pending"),
    failed: t("lp.ver.failed"),
    todo: t("lp.ver.notStarted"),
  }[state];
  return (
    <li className="flex items-center justify-between gap-3 py-2">
      <span className="text-sm text-slate-700">{label}</span>
      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tone}`}>{text}</span>
    </li>
  );
}

/** The four checks from the deck: register, beA code, ID, yearly re-check. */
export function VerificationTab({ me, onSaved }: { me: LawyerMe; onSaved: (me: LawyerMe) => void }) {
  const { t, locale } = useI18n();
  const v = me.verification;
  const [registerId, setRegisterId] = useState(me.profile.brak_register_id ?? "");
  const [chamber, setChamber] = useState(me.profile.chamber ?? "");
  const [admission, setAdmission] = useState(me.profile.admission_date ?? "");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<LawyerMe>) {
    setBusy(true);
    setError(null);
    try {
      onSaved(await action());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const idState =
    v.id_check_status === "passed"
      ? "done"
      : v.id_check_status === "failed"
        ? "failed"
        : v.id_check_status === "pending"
          ? "pending"
          : "todo";

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <h2 className="font-semibold text-slate-900">{t("lp.ver.title")}</h2>
        <p className="mt-1 text-sm text-slate-500">{t("lp.ver.lead")}</p>
        {v.is_suspended && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">
            {t("lp.ver.suspended")}
          </p>
        )}
        <ul className="mt-3 divide-y divide-slate-100">
          <Step label={t("lp.ver.register")} state={v.register_checked ? "done" : registerId ? "pending" : "todo"} />
          <Step
            label={t("lp.ver.bea")}
            state={v.bea_verified ? "done" : v.bea_code_sent ? "pending" : "todo"}
          />
          <Step label={t("lp.ver.id")} state={idState} />
          <Step label={t("lp.ver.recheck")} state={v.is_verified ? "done" : "todo"} />
        </ul>
        {v.verified_until && (
          <p className="mt-3 text-sm font-medium text-green-700">
            {t("lp.ver.validUntil", {
              date: new Date(v.verified_until).toLocaleDateString(locale),
            })}
          </p>
        )}
      </Card>

      <div className="flex flex-col gap-4">
        <Card>
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              void run(() =>
                api.updateLawyerProfile({
                  brak_register_id: registerId.trim() || null,
                  chamber: chamber.trim() || null,
                  admission_date: admission || null,
                }),
              );
            }}
          >
            <Field label={t("lp.ver.registerId")}>
              <Input value={registerId} onChange={(e) => setRegisterId(e.target.value)} maxLength={64} />
            </Field>
            <Field label={t("lp.ver.chamber")}>
              <Input
                value={chamber}
                onChange={(e) => setChamber(e.target.value)}
                maxLength={128}
                placeholder="Rechtsanwaltskammer München"
              />
            </Field>
            <Field label={t("lp.ver.admission")}>
              <Input type="date" value={admission} onChange={(e) => setAdmission(e.target.value)} />
            </Field>
            <div>
              <Button type="submit" disabled={busy}>
                {t("lp.ver.saveRegister")}
              </Button>
            </div>
          </form>
        </Card>

        {!v.bea_verified && (
          <Card>
            <h3 className="font-medium text-slate-800">{t("lp.ver.bea")}</h3>
            {v.bea_code_sent ? (
              <form
                className="mt-2 flex flex-col gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(() => api.confirmBeaCode(code));
                }}
              >
                <p className="text-sm text-slate-500">{t("lp.ver.beaHint")}</p>
                <Input
                  value={code}
                  onChange={(e) => setCode(e.target.value.toUpperCase())}
                  placeholder="XXXX-XXXX"
                  maxLength={12}
                  className="font-mono tracking-widest"
                  required
                />
                <div>
                  <Button type="submit" disabled={busy || code.length < 6}>
                    {t("lp.ver.beaSubmit")}
                  </Button>
                </div>
              </form>
            ) : (
              <p className="mt-2 text-sm text-slate-500">{t("lp.ver.beaWait")}</p>
            )}
          </Card>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
}
