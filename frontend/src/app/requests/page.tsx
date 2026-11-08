"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type ClientOrder } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { TranslationKey } from "@/lib/translations";
import { Button, Card, Spinner, Stars, StatusPill, Textarea } from "@/components/ui";

const STATUS_KEY: Record<ClientOrder["status"], TranslationKey> = {
  pending: "req.status.pending",
  accepted: "req.status.accepted",
  declined: "req.status.declined",
  cancelled: "req.status.cancelled",
  closed_won: "req.status.closed",
  closed_lost: "req.status.closed",
};

function ReviewForm({
  order,
  onDone,
}: {
  order: ClientOrder;
  onDone: (order: ClientOrder) => void;
}) {
  const { t } = useI18n();
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onDone(
        await api.reviewOrder(order.id, { rating, comment: comment.trim() || undefined }),
      );
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-3 flex flex-col gap-2 rounded-lg bg-slate-50 p-3">
      <p className="text-sm font-medium text-slate-700">
        {t("req.reviewPrompt", { name: order.lawyer.name })}
      </p>
      <Stars value={rating} onChange={setRating} size="text-2xl" />
      <Textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={2000}
        placeholder={t("req.reviewPlaceholder")}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div>
        <Button type="submit" disabled={busy || rating === 0}>
          {t("req.reviewSubmit")}
        </Button>
      </div>
    </form>
  );
}

export default function RequestsPage() {
  const { user, loading } = useRequireAuth();
  const { t, locale } = useI18n();
  const [orders, setOrders] = useState<ClientOrder[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api
      .myOrders()
      .then(setOrders)
      .catch((e) => setError(e.message));
  }, [user]);

  const replace = (updated: ClientOrder) =>
    setOrders((list) => (list ?? []).map((o) => (o.id === updated.id ? updated : o)));

  async function cancel(order: ClientOrder) {
    if (!window.confirm(t("req.cancelConfirm"))) return;
    try {
      replace(await api.cancelOrder(order.id));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (loading || !user)
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        {loading && <Spinner label={t("common.loading")} />}
      </div>
    );

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t("req.title")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("req.subtitle")}</p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {orders === null && !error && <Spinner label={t("common.loading")} />}

      {orders?.map((order) => (
        <Card key={order.id} className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-900">{order.lawyer.name}</h2>
              <p className="text-xs text-slate-500">
                {[order.lawyer.law_firm, order.lawyer.city].filter(Boolean).join(" · ")}
              </p>
            </div>
            <StatusPill status={order.status} label={t(STATUS_KEY[order.status])} />
          </div>
          <p className="mt-2 text-sm text-slate-700">
            {order.case_title ?? t("req.messageOnly")}
            <span className="text-slate-400">
              {" "}
              · {new Date(order.created_at).toLocaleDateString(locale)}
            </span>
          </p>
          {order.message && (
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-500">{order.message}</p>
          )}

          {order.status === "pending" && (
            <div className="mt-3 flex items-center gap-3">
              <p className="text-xs text-slate-500">{t("req.pendingHint")}</p>
              <Button variant="ghost" onClick={() => cancel(order)}>
                {t("req.cancel")}
              </Button>
            </div>
          )}
          {order.status === "accepted" && (
            <p className="mt-3 rounded-lg bg-brand-50/60 px-3 py-2 text-sm text-slate-700">
              {t("req.acceptedHint")}
              {(order.lawyer.email || order.lawyer.phone) && (
                <span className="mt-1 flex flex-wrap gap-4">
                  {order.lawyer.email && (
                    <a className="text-brand underline" href={`mailto:${order.lawyer.email}`}>
                      {order.lawyer.email}
                    </a>
                  )}
                  {order.lawyer.phone && (
                    <a className="text-brand underline" href={`tel:${order.lawyer.phone}`}>
                      {order.lawyer.phone}
                    </a>
                  )}
                </span>
              )}
            </p>
          )}
          {order.status === "declined" && (
            <p className="mt-3 text-sm text-slate-500">
              {t("req.declinedHint")}{" "}
              <Link href="/lawyers" className="text-brand underline">
                {t("home.findLawyer")}
              </Link>
            </p>
          )}

          {order.review && (
            <div className="mt-3 text-sm">
              <p className="text-xs font-medium text-slate-500">{t("req.yourReview")}</p>
              <Stars value={order.review.rating} />
              {order.review.comment && <p className="text-slate-600">{order.review.comment}</p>}
            </div>
          )}
          {order.can_review && <ReviewForm order={order} onDone={replace} />}
        </Card>
      ))}

      {orders?.length === 0 && (
        <Card className="text-center">
          <p className="text-sm text-slate-500">{t("req.empty")}</p>
          <Link href="/lawyers" className="mt-3 inline-block">
            <Button>{t("home.findLawyer")}</Button>
          </Link>
        </Card>
      )}
    </main>
  );
}
