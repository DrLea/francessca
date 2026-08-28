"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type LawyerPreview } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Input } from "@/components/ui";

/** Desktop builds are only offered once the URLs are configured at build
 *  time (NEXT_PUBLIC_DOWNLOAD_*), so the section never shows dead links. */
const DOWNLOADS = (
  [
    { label: "Windows", url: process.env.NEXT_PUBLIC_DOWNLOAD_WINDOWS },
    { label: "macOS", url: process.env.NEXT_PUBLIC_DOWNLOAD_MAC },
    { label: "Linux", url: process.env.NEXT_PUBLIC_DOWNLOAD_LINUX },
  ] as { label: string; url?: string }[]
).filter((d): d is { label: string; url: string } => !!d.url);

function Section({
  id,
  title,
  lead,
  children,
}: {
  id?: string;
  title: string;
  lead?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-slate-200/70 py-14">
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h2>
      {lead && <p className="mt-2 max-w-2xl text-sm text-slate-500">{lead}</p>}
      <div className="mt-6">{children}</div>
    </section>
  );
}

/** A still of the product: the one-question-at-a-time flow, rendered with
 *  the same styling as the real chat so the page shows rather than tells. */
function ChatPreview() {
  const { t } = useI18n();
  return (
    <div
      aria-hidden
      className="pointer-events-none select-none rounded-2xl border border-slate-200/80 bg-white p-4 shadow-soft"
    >
      <div className="mb-3 flex justify-end">
        <span className="max-w-[85%] rounded-2xl rounded-br-sm bg-brand px-3.5 py-2 text-xs text-white">
          {t("home.demoUser")}
        </span>
      </div>
      <div className="mb-3 flex">
        <span className="max-w-[85%] rounded-2xl rounded-bl-sm bg-slate-100 px-3.5 py-2 text-xs text-slate-700">
          {t("home.demoReply")}
        </span>
      </div>
      <div className="rounded-2xl border border-brand/30 bg-brand-50/40 p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-[11px] font-medium text-brand-700">
            {t("clarify.progress", { current: 1, total: 3 })}
          </span>
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-brand/60" />
            <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
            <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
          </span>
        </div>
        <p className="mb-2 text-xs font-medium text-slate-800">
          {t("home.demoQuestion")}
        </p>
        <div className="flex flex-col gap-1.5 text-xs">
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-slate-700">
            {t("home.demoChoice1")}
          </span>
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-slate-700">
            {t("home.demoChoice2")}
          </span>
          <span className="rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-slate-500">
            {t("clarify.other")}
          </span>
        </div>
      </div>
    </div>
  );
}

function Hero({ lawyerCount }: { lawyerCount: number }) {
  const { t, locale } = useI18n();
  const { user } = useAuth();

  const stats = [
    { value: "8", label: t("home.statLanguages") },
    ...(lawyerCount > 0
      ? [{ value: lawyerCount.toLocaleString(locale), label: t("home.statLawyers") }]
      : []),
    { value: "€0", label: t("home.statPrice") },
  ];

  return (
    <section className="relative my-8 overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-white p-8 sm:p-12">
      {/* Soft brand glow, purely decorative. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -end-24 -top-24 h-72 w-72 rounded-full bg-brand/10 blur-3xl"
      />
      <div className="relative grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <p className="mb-3 inline-block rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-brand-700 ring-1 ring-brand-100">
            {t("home.betaBadge")}
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            Franc<span className="text-brand">essca</span>
          </h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-slate-600">
            {t("home.tagline")}
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link href={user ? "/chat" : "/login"}>
              <Button>{user ? t("home.openChat") : t("home.getStarted")}</Button>
            </Link>
            <a href="#lawyers">
              <Button variant="secondary">{t("home.findLawyer")}</Button>
            </a>
            {DOWNLOADS.length > 0 && (
              <a href="#offline">
                <Button variant="ghost">{t("home.offlineTitle")}</Button>
              </a>
            )}
          </div>
          <dl className="mt-8 flex flex-wrap gap-x-8 gap-y-3">
            {stats.map((s) => (
              <div key={s.label}>
                <dt className="text-xl font-semibold text-slate-900">{s.value}</dt>
                <dd className="text-xs text-slate-500">{s.label}</dd>
              </div>
            ))}
          </dl>
        </div>
        <ChatPreview />
      </div>
    </section>
  );
}

function Steps() {
  const { t } = useI18n();
  const steps = [
    { title: t("home.step1Title"), body: t("home.step1Body") },
    { title: t("home.step2Title"), body: t("home.step2Body") },
    { title: t("home.step3Title"), body: t("home.step3Body") },
  ];
  return (
    <Section title={t("home.stepsTitle")}>
      <div className="grid gap-4 sm:grid-cols-3">
        {steps.map((s, i) => (
          <Card key={s.title} className="h-full transition-shadow duration-150 hover:shadow-lg">
            <span className="mb-3 inline-flex h-7 w-7 items-center justify-center rounded-full bg-brand text-sm font-semibold text-white">
              {i + 1}
            </span>
            <h3 className="font-medium text-slate-800">{s.title}</h3>
            <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{s.body}</p>
          </Card>
        ))}
      </div>
    </Section>
  );
}

function Lawyers({
  items,
  total,
}: {
  items: LawyerPreview[];
  total: number;
}) {
  const { t, locale } = useI18n();

  return (
    <Section
      id="lawyers"
      title={t("home.lawyersTitle")}
      lead={
        total > 0
          ? t("home.lawyersBody", { count: total.toLocaleString(locale) })
          : t("home.lawyersEmpty")
      }
    >
      {items.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((l) => (
            <Card
              key={l.id}
              className="py-4 transition-shadow duration-150 hover:shadow-lg"
            >
              <p className="font-medium text-slate-800">{l.name}</p>
              {(l.law_firm || l.city) && (
                <p className="text-xs text-slate-500">
                  {[l.law_firm, l.city].filter(Boolean).join(" · ")}
                </p>
              )}
              {l.specializations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {l.specializations.slice(0, 3).map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
      <div className="mt-5">
        <Link href="/lawyers">
          <Button variant="secondary">{t("home.lawyersCta")}</Button>
        </Link>
      </div>
    </Section>
  );
}

function Offline() {
  const { t } = useI18n();
  if (DOWNLOADS.length === 0) return null;
  return (
    <Section id="offline" title={t("home.offlineTitle")} lead={t("home.offlineBody")}>
      <div className="flex flex-wrap gap-3">
        {DOWNLOADS.map((d) => (
          <a key={d.label} href={d.url} download>
            <Button variant="secondary">
              {t("home.download", { platform: d.label })}
            </Button>
          </a>
        ))}
      </div>
    </Section>
  );
}

function Pricing() {
  const { t } = useI18n();
  const { user, refresh } = useAuth();
  const [saving, setSaving] = useState<"free" | "premium" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function choose(tier: "free" | "premium") {
    setSaving(tier);
    setError(null);
    try {
      await api.changePlan(tier);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(null);
    }
  }

  const plans = [
    {
      tier: "free" as const,
      name: t("home.planFree"),
      price: t("home.planFreePrice"),
      features: [t("home.planFreeF1"), t("home.planFreeF2"), t("home.planFreeF3")],
    },
    {
      tier: "premium" as const,
      name: t("home.planPremium"),
      price: t("home.planPremiumPrice"),
      features: [
        t("home.planPremiumF1"),
        t("home.planPremiumF2"),
        t("home.planPremiumF3"),
      ],
    },
  ];

  return (
    <Section id="pricing" title={t("home.pricingTitle")} lead={t("home.pricingBeta")}>
      <div className="grid gap-4 sm:grid-cols-2">
        {plans.map((plan) => {
          const current = user?.tier === plan.tier;
          return (
            <Card
              key={plan.tier}
              className={
                current
                  ? "border-brand ring-1 ring-brand/30"
                  : plan.tier === "premium"
                    ? "bg-gradient-to-br from-brand-50/60 to-white"
                    : undefined
              }
            >
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="font-semibold text-slate-800">{plan.name}</h3>
                <span className="text-sm font-medium text-brand-700">{plan.price}</span>
              </div>
              <ul className="mt-3 flex flex-col gap-1.5 text-sm text-slate-600">
                {plan.features.map((f) => (
                  <li key={f} className="flex gap-2">
                    <span aria-hidden className="text-brand">
                      ✓
                    </span>
                    {f}
                  </li>
                ))}
              </ul>
              <div className="mt-5">
                {!user ? (
                  <Link href="/login">
                    <Button variant="secondary">{t("home.planSignUp")}</Button>
                  </Link>
                ) : current ? (
                  <span className="text-xs font-medium text-slate-500">
                    {t("home.planCurrent")}
                  </span>
                ) : (
                  <Button disabled={saving !== null} onClick={() => choose(plan.tier)}>
                    {saving === plan.tier ? t("home.planActivating") : t("home.planActivate")}
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </Section>
  );
}

function LawyerSignup() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    email: "",
    law_firm: "",
    city: "",
    phone: "",
    website: "",
    specializations: "",
    languages: "",
    message: "",
  });

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const list = (value: string) =>
    value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      await api.applyAsLawyer({
        name: form.name.trim(),
        email: form.email.trim(),
        law_firm: form.law_firm.trim() || undefined,
        city: form.city.trim() || undefined,
        phone: form.phone.trim() || undefined,
        website: form.website.trim() || undefined,
        specializations: list(form.specializations),
        languages: list(form.languages),
        message: form.message.trim() || undefined,
      });
      setSent(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <Section
      id="for-lawyers"
      title={t("home.lawyerSignupTitle")}
      lead={t("home.lawyerSignupBody")}
    >
      {sent ? (
        <Card>
          <p className="text-sm text-green-700">{t("home.applicationSent")}</p>
        </Card>
      ) : !open ? (
        <Button variant="secondary" onClick={() => setOpen(true)}>
          {t("home.lawyerSignupCta")}
        </Button>
      ) : (
        <Card>
          <form onSubmit={submit} className="flex flex-col gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                required
                value={form.name}
                onChange={set("name")}
                placeholder={t("home.fieldName")}
              />
              <Input
                required
                type="email"
                value={form.email}
                onChange={set("email")}
                placeholder={t("home.fieldEmail")}
              />
              <Input
                value={form.law_firm}
                onChange={set("law_firm")}
                placeholder={t("home.fieldFirm")}
              />
              <Input
                value={form.city}
                onChange={set("city")}
                placeholder={t("home.fieldCity")}
              />
              <Input
                value={form.phone}
                onChange={set("phone")}
                placeholder={t("home.fieldPhone")}
              />
              <Input
                value={form.website}
                onChange={set("website")}
                placeholder={t("home.fieldWebsite")}
              />
              <Input
                value={form.specializations}
                onChange={set("specializations")}
                placeholder={t("home.fieldSpecializations")}
              />
              <Input
                value={form.languages}
                onChange={set("languages")}
                placeholder={t("home.fieldLanguages")}
              />
            </div>
            <Input
              value={form.message}
              onChange={set("message")}
              placeholder={t("home.fieldMessage")}
            />
            <p className="text-xs text-slate-400">{t("home.reviewNote")}</p>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex items-center gap-2">
              <Button type="submit" disabled={sending}>
                {sending ? t("home.submitting") : t("home.submitApplication")}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                {t("timeline.cancel")}
              </Button>
            </div>
          </form>
        </Card>
      )}
    </Section>
  );
}

export default function HomePage() {
  const { t } = useI18n();
  const [lawyers, setLawyers] = useState<{ items: LawyerPreview[]; total: number }>({
    items: [],
    total: 0,
  });

  // One fetch feeds both the hero counter and the preview cards.
  useEffect(() => {
    api.publicLawyers(6).then(setLawyers).catch(() => {});
  }, []);

  return (
    <main className="mx-auto max-w-5xl px-6 pb-16">
      <Hero lawyerCount={lawyers.total} />
      <Steps />
      <Lawyers items={lawyers.items} total={lawyers.total} />
      <Offline />
      <Pricing />
      <LawyerSignup />
      <footer className="border-t border-slate-200/70 py-8 text-xs leading-relaxed text-slate-400">
        {t("common.disclaimer")}
      </footer>
    </main>
  );
}
