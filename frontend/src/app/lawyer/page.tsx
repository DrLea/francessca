"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type DesktopDownload,
  type Feedback,
  type LawyerMe,
  type LawyerOrder,
  type LawyerStats,
} from "@/lib/api";
import { useRequireRole } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { usePwa } from "@/lib/pwa";
import { Button, Card, Spinner, Stars, StatusPill, Tabs, VerifiedBadge } from "@/components/ui";
import {
  CATEGORY_KEY,
  FeedbackButton,
  FeedbackDialog,
} from "@/components/lawyer/FeedbackButton";
import { OrdersTab } from "@/components/lawyer/OrdersTab";
import { ProfileTab } from "@/components/lawyer/ProfileTab";
import { FinanceTab, StatsTab } from "@/components/lawyer/StatsTab";
import { VerificationTab, subscriptionLine } from "@/components/lawyer/VerificationTab";

type Tab = "orders" | "deals" | "stats" | "finance" | "profile" | "verification" | "feedback";

/** Install the portal as a desktop app (it is a PWA), or fetch the offline
 *  build when one is published. */
function DesktopApp() {
  const { t } = useI18n();
  const { canInstall, installed, install } = usePwa();
  const [downloads, setDownloads] = useState<DesktopDownload[]>([]);

  useEffect(() => {
    api
      .desktopDownloads()
      .then((res) => setDownloads(res.items))
      .catch(() => {});
  }, []);

  if (installed && downloads.length === 0) return null;
  return (
    <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
      <div className="min-w-0">
        <p className="font-medium text-slate-900">{t("lp.desktop.title")}</p>
        <p className="text-xs text-slate-500">
          {canInstall || installed ? t("lp.desktop.body") : t("lp.desktop.manual")}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {canInstall && <Button onClick={() => void install()}>{t("lp.desktop.install")}</Button>}
        {downloads.map((d) => (
          <a key={d.platform} href={d.url} download>
            <Button variant="secondary">
              {t("lp.desktop.offline", {
                platform: { windows: "Windows", mac: "macOS", linux: "Linux" }[d.platform],
              })}
            </Button>
          </a>
        ))}
      </div>
    </Card>
  );
}

export default function LawyerPortalPage() {
  const { user, loading } = useRequireRole("lawyer");
  const { t, locale } = useI18n();
  const [tab, setTab] = useState<Tab>("orders");
  const [me, setMe] = useState<LawyerMe | null>(null);
  const [orders, setOrders] = useState<LawyerOrder[]>([]);
  const [stats, setStats] = useState<LawyerStats | null>(null);
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [error, setError] = useState<string | null>(null);
  // undefined = closed; null = open with no order pre-selected.
  const [feedbackFor, setFeedbackFor] = useState<number | null | undefined>(undefined);

  const load = useCallback(async () => {
    try {
      const [m, o, s, f] = await Promise.all([
        api.lawyerMe(),
        api.lawyerOrders(),
        api.lawyerStats(),
        api.lawyerFeedback(),
      ]);
      setMe(m);
      setOrders(o);
      setStats(s);
      setFeedback(f);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  if (loading || !user || !me || !stats)
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-2">
        {error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : (
          <Spinner label={t("common.loading")} />
        )}
      </div>
    );

  const { subscription, profile } = me;
  const pending = orders.filter((o) => o.status === "pending").length;

  // One order changed: swap it in, then refresh the numbers that depend on it.
  const onOrderChange = (updated: LawyerOrder) => {
    setOrders((list) => list.map((o) => (o.id === updated.id ? updated : o)));
    void Promise.all([api.lawyerMe(), api.lawyerStats()])
      .then(([m, s]) => {
        setMe(m);
        setStats(s);
      })
      .catch(() => {});
  };

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-5 px-6 pb-24 pt-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            {profile.name}
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
            {[profile.law_firm, profile.city].filter(Boolean).join(" · ")}
            <StatusPill status={me.approval} label={t(`lp.approval.${me.approval}`)} />
            {me.verification.is_verified && <VerifiedBadge label={t("lawyers.verified")} />}
            {profile.rating_avg != null && (
              <span className="flex items-center gap-1">
                <Stars value={profile.rating_avg} size="text-sm" />
                {profile.rating_avg.toFixed(1)} ({profile.rating_count})
              </span>
            )}
          </p>
        </div>
        <div className="rounded-xl border border-brand-100 bg-brand-50/60 px-4 py-2 text-end">
          <div className="text-lg font-bold text-brand-700">
            {subscriptionLine(subscription, t, locale)}
          </div>
          <div className="text-xs text-slate-500">
            {t("lp.sub.caption", {
              fee: subscription.monthly_fee,
              months: subscription.trial_months,
            })}
          </div>
        </div>
      </div>

      {me.verification.is_suspended && (
        <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">
          {t("lp.ver.suspended")}
        </div>
      )}

      {me.approval !== "approved" && (
        <div
          className={
            "rounded-xl px-4 py-3 text-sm " +
            (me.approval === "rejected"
              ? "bg-red-50 text-red-800"
              : "bg-amber-50 text-amber-800")
          }
        >
          {me.approval === "rejected" ? t("lp.banner.rejected") : t("lp.banner.pending")}{" "}
          {me.approval === "pending" && me.profile_completeness < 80 && (
            <button className="font-medium underline" onClick={() => setTab("profile")}>
              {t("lp.banner.completeProfile")}
            </button>
          )}
        </div>
      )}

      <DesktopApp />

      <Tabs<Tab>
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "orders", label: t("lp.tab.orders"), count: pending },
          { id: "deals", label: t("lp.tab.deals") },
          { id: "stats", label: t("lp.tab.stats") },
          { id: "finance", label: t("lp.tab.finance") },
          { id: "profile", label: t("lp.tab.profile") },
          { id: "verification", label: t("lp.tab.verification") },
          { id: "feedback", label: t("lp.tab.feedback") },
        ]}
      />

      {(tab === "orders" || tab === "deals") && (
        <OrdersTab
          orders={orders}
          me={me}
          closedOnly={tab === "deals"}
          onChange={onOrderChange}
          onFeedback={(id) => setFeedbackFor(id)}
        />
      )}
      {tab === "stats" && <StatsTab stats={stats} me={me} />}
      {tab === "finance" && <FinanceTab stats={stats} me={me} orders={orders} />}
      {tab === "profile" && <ProfileTab me={me} onSaved={setMe} />}
      {tab === "verification" && <VerificationTab me={me} onSaved={setMe} />}
      {tab === "feedback" && (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-slate-500">{t("lp.fb.historyLead")}</p>
          {feedback.map((f) => (
            <Card key={f.id} className="p-4">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span className="font-medium text-slate-700">{t(CATEGORY_KEY[f.category])}</span>
                {f.rating != null && <Stars value={f.rating} size="text-sm" />}
                <span>{new Date(f.created_at).toLocaleDateString(locale)}</span>
                {f.order_id != null && <span>#{f.order_id}</span>}
                <StatusPill status={f.status} label={t(`lp.fb.status.${f.status}`)} />
              </div>
              <p className="whitespace-pre-wrap text-sm text-slate-700">{f.comment}</p>
            </Card>
          ))}
          {feedback.length === 0 && (
            <Card className="text-center text-sm text-slate-500">{t("lp.fb.historyEmpty")}</Card>
          )}
        </div>
      )}

      <FeedbackButton onClick={() => setFeedbackFor(null)} />
      {feedbackFor !== undefined && (
        <FeedbackDialog
          orders={orders}
          orderId={feedbackFor ?? undefined}
          onClose={() => setFeedbackFor(undefined)}
          onSent={() =>
            void api
              .lawyerFeedback()
              .then(setFeedback)
              .catch(() => {})
          }
        />
      )}
    </main>
  );
}
