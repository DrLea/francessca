"use client";

import { type LawyerMe, type LawyerOrder, type LawyerStats } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Card, Stars, Stat } from "@/components/ui";
import { subscriptionLine } from "@/components/lawyer/VerificationTab";

const pct = (value: number | null) => (value == null ? "—" : `${Math.round(value * 100)}%`);

function monthLabel(month: string, locale: string) {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(locale, { month: "short" });
}

/** Plain CSS bars: one group per month, tallest value sets the scale. */
function MonthlyBars({
  data,
  series,
  format = (v: number) => String(v),
}: {
  data: LawyerStats["monthly"];
  series: { key: "received" | "accepted" | "won" | "revenue"; label: string; tone: string }[];
  format?: (v: number) => string;
}) {
  const { locale } = useI18n();
  const max = Math.max(1, ...data.flatMap((d) => series.map((s) => d[s.key])));
  return (
    <div>
      <div className="flex h-40 items-end gap-3">
        {data.map((d) => (
          <div key={d.month} className="flex h-full flex-1 flex-col justify-end">
            <div className="flex h-full items-end justify-center gap-1">
              {series.map((s) => (
                <div
                  key={s.key}
                  title={`${s.label}: ${format(d[s.key])}`}
                  className={`w-full max-w-[22px] rounded-t ${s.tone}`}
                  style={{ height: `${Math.max(d[s.key] > 0 ? 4 : 0, (d[s.key] / max) * 100)}%` }}
                />
              ))}
            </div>
            <div className="mt-1.5 text-center text-[11px] text-slate-400">
              {monthLabel(d.month, locale)}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
        {series.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-sm ${s.tone}`} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function StatsTab({ stats, me }: { stats: LawyerStats; me: LawyerMe }) {
  const { t } = useI18n();
  const { orders, rates, rating } = stats;
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat value={orders.received} label={t("lp.stats.received")} />
        <Stat
          value={pct(rates.acceptance)}
          label={t("lp.stats.acceptance")}
          hint={t("lp.stats.acceptanceHint", {
            accepted: orders.accepted,
            declined: orders.declined,
          })}
        />
        <Stat
          value={pct(rates.win)}
          label={t("lp.stats.winRate")}
          hint={t("lp.stats.winHint", { won: orders.won, lost: orders.lost })}
        />
        <Stat
          value={rates.avg_lead_quality ?? "—"}
          label={t("lp.stats.leadQuality")}
          hint={t("lp.stats.leadQualityHint")}
        />
        <Stat value={orders.pending} label={t("lp.stats.waiting")} />
        <Stat value={orders.in_progress} label={t("lp.stats.inProgress")} />
        <Stat
          value={rates.avg_response_hours == null ? "—" : `${rates.avg_response_hours} h`}
          label={t("lp.stats.responseTime")}
        />
        <Stat
          value={
            rating.average == null ? (
              "—"
            ) : (
              <span className="flex items-center gap-2">
                {rating.average.toFixed(1)} <Stars value={rating.average} />
              </span>
            )
          }
          label={t("lp.stats.rating", { count: rating.count })}
        />
      </div>

      <Card>
        <h3 className="mb-4 font-semibold text-slate-900">{t("lp.stats.monthly")}</h3>
        <MonthlyBars
          data={stats.monthly}
          series={[
            { key: "received", label: t("lp.stats.received"), tone: "bg-slate-300" },
            { key: "accepted", label: t("lp.stats.accepted"), tone: "bg-brand-300" },
            { key: "won", label: t("lp.stats.won"), tone: "bg-brand" },
          ]}
        />
      </Card>

      <Card>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">{t("lp.stats.profile")}</h3>
          <span className="text-sm text-slate-500">{me.profile_completeness}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-brand"
            style={{ width: `${me.profile_completeness}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500">{t("lp.stats.profileHint")}</p>
      </Card>
    </div>
  );
}

export function FinanceTab({
  stats,
  me,
  orders,
}: {
  stats: LawyerStats;
  me: LawyerMe;
  orders: LawyerOrder[];
}) {
  const { t, locale } = useI18n();
  const money = (v: number) =>
    v.toLocaleString(locale, { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
  const { finance } = stats;
  const { subscription } = me;
  const deals = orders.filter((o) => o.status === "closed_won");

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat
          value={money(finance.revenue)}
          label={t("lp.fin.revenue")}
          hint={t("lp.fin.revenueHint")}
        />
        <Stat value={finance.deals} label={t("lp.fin.deals")} />
        <Stat
          value={finance.avg_deal == null ? "—" : money(finance.avg_deal)}
          label={t("lp.fin.avgDeal")}
        />
        <Stat
          value={subscription.state === "trial" ? money(0) : money(subscription.monthly_fee)}
          label={t("lp.fin.subscription")}
          hint={t("lp.fin.flat")}
        />
      </div>

      <Card>
        <h3 className="mb-2 font-semibold text-slate-900">{t("lp.fin.subscription")}</h3>
        <p className="text-xl font-bold text-slate-900">{subscriptionLine(subscription, t, locale)}</p>
        <p className="mt-1 text-sm text-slate-500">
          {t("lp.sub.caption", { fee: subscription.monthly_fee, months: subscription.trial_months })}
        </p>
        {subscription.state === "expired" && (
          <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {t("lp.paywall.expiredBody", { fee: subscription.monthly_fee })}
            {subscription.contact_email && (
              <>
                {" "}
                <a className="font-medium underline" href={`mailto:${subscription.contact_email}`}>
                  {subscription.contact_email}
                </a>
              </>
            )}
          </p>
        )}
      </Card>

      <Card>
        <h3 className="mb-4 font-semibold text-slate-900">{t("lp.fin.monthly")}</h3>
        <MonthlyBars
          data={stats.monthly}
          series={[{ key: "revenue", label: t("lp.fin.revenue"), tone: "bg-brand" }]}
          format={money}
        />
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold text-slate-900">{t("lp.fin.dealList")}</h3>
        {deals.length === 0 ? (
          <p className="text-sm text-slate-500">{t("lp.deals.empty")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-slate-100">
                {deals.map((o) => (
                  <tr key={o.id}>
                    <td className="py-2 pe-3 text-slate-500">
                      {new Date(o.closed_at ?? o.created_at).toLocaleDateString(locale)}
                    </td>
                    <td className="py-2 pe-3 text-slate-800">
                      {o.case_title ?? t("lp.orders.messageOnly")}
                    </td>
                    <td className="py-2 pe-3 text-slate-500">{o.client?.name ?? o.client?.email}</td>
                    <td className="py-2 text-end font-medium tabular-nums text-slate-900">
                      {o.deal_value == null ? "—" : money(o.deal_value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
