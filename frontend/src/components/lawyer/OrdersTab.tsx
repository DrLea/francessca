"use client";

import { useState } from "react";
import { api, ApiError, type LawyerMe, type LawyerOrder } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { TranslationKey } from "@/lib/translations";
import {
  Button,
  Card,
  Input,
  Modal,
  QualityMeter,
  Stars,
  StatusPill,
} from "@/components/ui";

export const STATUS_KEY: Record<LawyerOrder["status"], TranslationKey> = {
  pending: "lp.status.pending",
  accepted: "lp.status.accepted",
  declined: "lp.status.declined",
  cancelled: "lp.status.cancelled",
  closed_won: "lp.status.closedWon",
  closed_lost: "lp.status.closedLost",
};

const BREAKDOWN_KEY: Record<string, TranslationKey> = {
  narrative: "lp.q.narrative",
  timeline: "lp.q.timeline",
  documents: "lp.q.documents",
  dates: "lp.q.dates",
  people: "lp.q.people",
  questions: "lp.q.questions",
  case_type: "lp.q.caseType",
  message: "lp.q.message",
};
const BREAKDOWN_MAX: Record<string, number> = {
  narrative: 20,
  timeline: 15,
  documents: 20,
  dates: 10,
  people: 10,
  questions: 10,
  case_type: 5,
  message: 10,
};

const SUMMARY_LISTS: [string, TranslationKey][] = [
  ["timeline", "lp.sum.timeline"],
  ["people_involved", "lp.sum.people"],
  ["important_dates", "lp.sum.dates"],
  ["documents_available", "lp.sum.documents"],
  ["missing_documents", "lp.sum.missing"],
  ["questions_for_lawyer", "lp.sum.questions"],
];

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v) => typeof v === "string" && v) : [];
}

function Paywall({ me, onClose }: { me: LawyerMe; onClose: () => void }) {
  const { t } = useI18n();
  const email = me.quota.contact_email;
  return (
    <Modal title={t("lp.paywall.title")} onClose={onClose}>
      <p className="text-sm leading-relaxed text-slate-600">
        {t("lp.paywall.body", { count: me.quota.free_total })}
      </p>
      <div className="mt-5 flex flex-wrap gap-2">
        {email && (
          <a
            href={`mailto:${email}?subject=${encodeURIComponent(
              `Francessca: more orders for ${me.profile.name}`,
            )}`}
          >
            <Button>{t("lp.paywall.cta")}</Button>
          </a>
        )}
        <Button variant="ghost" onClick={onClose}>
          {t("lp.close")}
        </Button>
      </div>
      {email && <p className="mt-3 text-xs text-slate-400">{email}</p>}
    </Modal>
  );
}

function CloseDialog({
  order,
  onClose,
  onDone,
}: {
  order: LawyerOrder;
  onClose: () => void;
  onDone: (order: LawyerOrder) => void;
}) {
  const { t } = useI18n();
  const [outcome, setOutcome] = useState<"won" | "lost">(
    order.status === "closed_lost" ? "lost" : "won",
  );
  const [value, setValue] = useState(order.deal_value != null ? String(order.deal_value) : "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const amount = Number(value.replace(",", "."));
      onDone(
        await api.closeOrder(order.id, {
          outcome,
          deal_value:
            outcome === "won" && value.trim() && Number.isFinite(amount) ? amount : undefined,
        }),
      );
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <Modal title={t("lp.close.title")} onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-2">
          {(["won", "lost"] as const).map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => setOutcome(o)}
              className={
                "rounded-xl border px-3 py-3 text-sm font-medium transition-colors " +
                (outcome === o
                  ? "border-brand bg-brand-50 text-brand-700"
                  : "border-slate-200 text-slate-600 hover:bg-slate-50")
              }
            >
              {o === "won" ? t("lp.close.won") : t("lp.close.lost")}
            </button>
          ))}
        </div>
        {outcome === "won" && (
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-slate-600">{t("lp.close.value")}</span>
            <Input
              inputMode="decimal"
              placeholder="1500"
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
            <span className="text-[11px] text-slate-400">{t("lp.close.valueHint")}</span>
          </label>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex gap-2">
          <Button type="submit" disabled={busy}>
            {t("timeline.save")}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            {t("timeline.cancel")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function OrderCard({
  order,
  me,
  onChange,
  onPaywall,
  onFeedback,
}: {
  order: LawyerOrder;
  me: LawyerMe;
  onChange: (order: LawyerOrder) => void;
  onPaywall: () => void;
  onFeedback: (orderId: number) => void;
}) {
  const { t, locale } = useI18n();
  const [open, setOpen] = useState(order.status === "pending");
  const [busy, setBusy] = useState<"accept" | "decline" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [closing, setClosing] = useState(false);

  const summary = order.case_summary ?? {};
  const narrative = typeof summary.narrative === "string" ? summary.narrative : "";
  const closed = order.status === "closed_won" || order.status === "closed_lost";

  async function respond(action: "accept" | "decline") {
    if (action === "accept" && me.quota.remaining <= 0) return onPaywall();
    setBusy(action);
    setError(null);
    try {
      onChange(
        action === "accept" ? await api.acceptOrder(order.id) : await api.declineOrder(order.id),
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) onPaywall();
      else setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="p-5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full flex-wrap items-center justify-between gap-x-4 gap-y-2 text-start"
      >
        <div className="min-w-0">
          <p className="truncate font-medium text-slate-900">
            {order.case_title ?? t("lp.orders.messageOnly")}
          </p>
          <p className="text-xs text-slate-500">
            #{order.id} · {new Date(order.created_at).toLocaleDateString(locale)}
            {order.case_type ? ` · ${order.case_type}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <QualityMeter score={order.quality_score} label={t("lp.orders.quality")} />
          <StatusPill status={order.status} label={t(STATUS_KEY[order.status])} />
        </div>
      </button>

      {open && (
        <div className="mt-4 flex flex-col gap-4 border-t border-slate-100 pt-4 text-sm">
          {order.message && (
            <div>
              <p className="mb-1 text-xs font-medium text-slate-500">{t("lp.orders.message")}</p>
              <p className="whitespace-pre-wrap text-slate-700">{order.message}</p>
            </div>
          )}
          {narrative && (
            <div>
              <p className="mb-1 text-xs font-medium text-slate-500">{t("lp.sum.narrative")}</p>
              <p className="whitespace-pre-wrap leading-relaxed text-slate-700">{narrative}</p>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            {SUMMARY_LISTS.map(([key, label]) => {
              const items = strings(summary[key]);
              if (items.length === 0) return null;
              return (
                <div key={key}>
                  <p className="mb-1 text-xs font-medium text-slate-500">{t(label)}</p>
                  <ul className="list-disc ps-4 text-slate-700">
                    {items.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>

          <details className="rounded-lg bg-slate-50 px-3 py-2">
            <summary className="cursor-pointer text-xs font-medium text-slate-600">
              {t("lp.orders.qualityWhy", { score: order.quality_score })}
            </summary>
            <div className="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-2">
              {Object.keys(BREAKDOWN_MAX).map((key) => (
                <div key={key} className="flex justify-between text-xs text-slate-600">
                  <span>{t(BREAKDOWN_KEY[key])}</span>
                  <span className="tabular-nums text-slate-500">
                    {order.quality_breakdown?.[key] ?? 0} / {BREAKDOWN_MAX[key]}
                  </span>
                </div>
              ))}
            </div>
          </details>

          {order.client ? (
            <div className="rounded-lg border border-brand-100 bg-brand-50/50 px-3 py-2">
              <p className="text-xs font-medium text-brand-700">{t("lp.orders.client")}</p>
              <p className="text-slate-800">
                {order.client.name ?? "—"} ·{" "}
                <a className="text-brand underline" href={`mailto:${order.client.email}`}>
                  {order.client.email}
                </a>
              </p>
            </div>
          ) : (
            order.status === "pending" && (
              <p className="text-xs text-slate-500">{t("lp.orders.contactHidden")}</p>
            )
          )}

          {order.status === "closed_won" && order.deal_value != null && (
            <p className="text-slate-700">
              {t("lp.orders.dealValue")}:{" "}
              <span className="font-semibold">
                {order.deal_value.toLocaleString(locale, { style: "currency", currency: "EUR" })}
              </span>
            </p>
          )}
          {order.review && (
            <div>
              <p className="mb-1 text-xs font-medium text-slate-500">{t("lp.orders.review")}</p>
              <Stars value={order.review.rating} />
              {order.review.comment && (
                <p className="mt-1 text-slate-700">“{order.review.comment}”</p>
              )}
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex flex-wrap items-center gap-2">
            {order.status === "pending" && (
              <>
                <Button disabled={busy !== null} onClick={() => respond("accept")}>
                  {busy === "accept" ? t("lp.sending") : t("lp.orders.accept")}
                </Button>
                <Button
                  variant="ghost"
                  disabled={busy !== null}
                  onClick={() => respond("decline")}
                >
                  {t("lp.orders.decline")}
                </Button>
                <span className="text-xs text-slate-400">
                  {me.quota.free_remaining > 0
                    ? t("lp.orders.freeNote", { count: me.quota.free_remaining })
                    : t("lp.orders.usesOne")}
                </span>
              </>
            )}
            {(order.status === "accepted" || closed) && (
              <Button variant="secondary" onClick={() => setClosing(true)}>
                {closed ? t("lp.orders.editOutcome") : t("lp.orders.close")}
              </Button>
            )}
            <Button variant="ghost" onClick={() => onFeedback(order.id)}>
              {t("lp.orders.rateLead")}
            </Button>
          </div>
        </div>
      )}

      {closing && (
        <CloseDialog
          order={order}
          onClose={() => setClosing(false)}
          onDone={(updated) => {
            setClosing(false);
            onChange(updated);
          }}
        />
      )}
    </Card>
  );
}

type Filter = "open" | "pending" | "accepted" | "closed" | "all";

export function OrdersTab({
  orders,
  me,
  closedOnly = false,
  onChange,
  onFeedback,
}: {
  orders: LawyerOrder[];
  me: LawyerMe;
  /** The "Closed deals" tab: the same list, limited to closed orders. */
  closedOnly?: boolean;
  onChange: (order: LawyerOrder) => void;
  onFeedback: (orderId: number) => void;
}) {
  const { t } = useI18n();
  const [filter, setFilter] = useState<Filter>("open");
  const [paywall, setPaywall] = useState(false);

  const isClosed = (o: LawyerOrder) => o.status === "closed_won" || o.status === "closed_lost";
  const visible = orders.filter((o) => {
    if (closedOnly) return isClosed(o);
    if (filter === "all") return true;
    if (filter === "closed") return isClosed(o) || o.status === "declined";
    if (filter === "open") return o.status === "pending" || o.status === "accepted";
    return o.status === filter;
  });

  const filters: [Filter, TranslationKey][] = [
    ["open", "lp.filter.open"],
    ["pending", "lp.filter.pending"],
    ["accepted", "lp.filter.accepted"],
    ["closed", "lp.filter.closed"],
    ["all", "lp.filter.all"],
  ];

  return (
    <div className="flex flex-col gap-3">
      {!closedOnly && (
        <div className="flex flex-wrap gap-1.5">
          {filters.map(([id, key]) => (
            <button
              key={id}
              onClick={() => setFilter(id)}
              className={
                "rounded-full px-3 py-1 text-xs font-medium transition-colors " +
                (filter === id
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200")
              }
            >
              {t(key)}
            </button>
          ))}
        </div>
      )}
      {visible.map((order) => (
        <OrderCard
          key={order.id}
          order={order}
          me={me}
          onChange={onChange}
          onPaywall={() => setPaywall(true)}
          onFeedback={onFeedback}
        />
      ))}
      {visible.length === 0 && (
        <Card className="text-center text-sm text-slate-500">
          {closedOnly
            ? t("lp.deals.empty")
            : orders.length === 0
              ? me.approval === "approved"
                ? t("lp.orders.emptyLive")
                : t("lp.orders.emptyPending")
              : t("lp.orders.emptyFilter")}
        </Card>
      )}
      {paywall && <Paywall me={me} onClose={() => setPaywall(false)} />}
    </div>
  );
}
