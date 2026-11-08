"use client";

import { useState } from "react";
import { api, type FeedbackCategory, type LawyerOrder } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { TranslationKey } from "@/lib/translations";
import { Button, Field, Modal, Select, Stars, Textarea } from "@/components/ui";

const CATEGORIES: FeedbackCategory[] = ["lead_quality", "platform", "idea", "bug", "other"];

export const CATEGORY_KEY: Record<FeedbackCategory, TranslationKey> = {
  lead_quality: "lp.fb.catLeadQuality",
  platform: "lp.fb.catPlatform",
  idea: "lp.fb.catIdea",
  bug: "lp.fb.catBug",
  other: "lp.fb.catOther",
};

/** The quick-comment dialog. Opened from the floating button, or from an
 *  order (which then arrives pre-selected). */
export function FeedbackDialog({
  orders,
  orderId,
  onClose,
  onSent,
}: {
  orders: LawyerOrder[];
  orderId?: number;
  onClose: () => void;
  onSent?: () => void;
}) {
  const t = useT();
  const [category, setCategory] = useState<FeedbackCategory>("lead_quality");
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [order, setOrder] = useState<string>(orderId ? String(orderId) : "");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      await api.sendFeedback({
        category,
        comment: comment.trim(),
        rating: rating || undefined,
        order_id: order ? Number(order) : undefined,
      });
      setSent(true);
      onSent?.();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <Modal title={t("lp.fb.title")} onClose={onClose}>
      {sent ? (
        <div className="flex flex-col items-start gap-4">
          <p className="text-sm text-green-700">{t("lp.fb.thanks")}</p>
          <Button variant="secondary" onClick={onClose}>
            {t("lp.close")}
          </Button>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <p className="text-sm text-slate-500">{t("lp.fb.lead")}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t("lp.fb.about")}>
              <Select
                value={category}
                onChange={(e) => setCategory(e.target.value as FeedbackCategory)}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {t(CATEGORY_KEY[c])}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t("lp.fb.rating")}>
              <Stars value={rating} onChange={setRating} size="text-2xl" />
            </Field>
          </div>
          {orders.length > 0 && (
            <Field label={t("lp.fb.order")}>
              <Select value={order} onChange={(e) => setOrder(e.target.value)}>
                <option value="">{t("lp.fb.orderNone")}</option>
                {orders.map((o) => (
                  <option key={o.id} value={o.id}>
                    #{o.id} · {o.case_title ?? t("lp.orders.messageOnly")}
                  </option>
                ))}
              </Select>
            </Field>
          )}
          <Field label={t("lp.fb.comment")}>
            <Textarea
              required
              minLength={3}
              maxLength={4000}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t("lp.fb.placeholder")}
              className="min-h-[96px]"
            />
          </Field>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={sending || comment.trim().length < 3}>
              {sending ? t("lp.sending") : t("lp.fb.send")}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              {t("timeline.cancel")}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

/** Always-there button in the corner of the lawyer portal. */
export function FeedbackButton({ onClick }: { onClick: () => void }) {
  const t = useT();
  return (
    <button
      type="button"
      onClick={onClick}
      className="fixed bottom-5 end-5 z-20 flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2.5 text-sm font-medium text-white shadow-lg transition-transform hover:-translate-y-0.5 active:scale-95"
    >
      <span aria-hidden>✎</span>
      {t("lp.fb.button")}
    </button>
  );
}
