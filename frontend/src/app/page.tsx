"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type DesktopDownload, type LawyerPreview } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { InstallApp } from "@/components/InstallApp";
import { Button, Card, VerifiedBadge } from "@/components/ui";

const PLATFORM_LABEL: Record<DesktopDownload["platform"], string> = {
  windows: "Windows",
  mac: "macOS",
  linux: "Linux",
};

/** Build-time fallback, for a deployment that has no backend reachable yet.
 *  The live list comes from GET /public/downloads, so publishing a release
 *  needs no frontend rebuild. */
const STATIC_DOWNLOADS = (
  [
    { platform: "windows", url: process.env.NEXT_PUBLIC_DOWNLOAD_WINDOWS },
    { platform: "mac", url: process.env.NEXT_PUBLIC_DOWNLOAD_MAC },
    { platform: "linux", url: process.env.NEXT_PUBLIC_DOWNLOAD_LINUX },
  ] as { platform: DesktopDownload["platform"]; url?: string }[]
)
  .filter((d): d is { platform: DesktopDownload["platform"]; url: string } => !!d.url)
  .map((d) => ({ ...d, sha256: null }));

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
          <h1 className="flex items-center gap-4 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/brand/mark.png"
              alt=""
              width={64}
              height={64}
              className="h-14 w-14 rounded-2xl shadow-soft sm:h-16 sm:w-16"
            />
            <span>
              Franc<span className="text-brand">esca</span>
            </span>
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
            {STATIC_DOWNLOADS.length > 0 && (
              <a href="#offline">
                <Button variant="ghost">{t("home.offlineTitle")}</Button>
              </a>
            )}
          </div>
          {!user && (
            <p className="mt-4 text-sm text-slate-500">
              {t("nav.areYouLawyer")}{" "}
              <Link href="/lawyer/register" className="font-medium text-brand underline">
                {t("home.lawyerJoinLink")}
              </Link>
            </p>
          )}
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
              <p className="flex flex-wrap items-center gap-2 font-medium text-slate-800">
                {l.name}
                {l.is_verified && (
                  <VerifiedBadge label={t("lawyers.verified")} hint={t("lawyers.verifiedHint")} />
                )}
              </p>
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
  const [downloads, setDownloads] = useState<DesktopDownload[]>(STATIC_DOWNLOADS);
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    api
      .desktopDownloads()
      .then((res) => {
        if (res.items.length > 0) setDownloads(res.items);
        setVersion(res.version);
      })
      .catch(() => {});
  }, []);

  // Nothing published yet: no section at all, rather than a dead button.
  if (downloads.length === 0) return null;

  return (
    <Section
      id="offline"
      title={t("home.offlineTitle")}
      lead={
        version
          ? `${t("home.offlineBody")} ${t("home.version", { version })}`
          : t("home.offlineBody")
      }
    >
      <div className="flex flex-wrap gap-3">
        {downloads.map((d) => (
          <a key={d.platform} href={d.url} download>
            <Button variant="secondary">
              {t("home.download", { platform: PLATFORM_LABEL[d.platform] })}
            </Button>
          </a>
        ))}
      </div>
      {downloads.some((d) => d.sha256) && (
        <div className="mt-4 flex flex-col gap-1">
          <p className="text-xs text-slate-500">{t("home.checksums")}</p>
          {downloads
            .filter((d) => d.sha256)
            .map((d) => (
              <p key={d.platform} className="font-mono text-[11px] text-slate-400">
                <span className="text-slate-500">{PLATFORM_LABEL[d.platform]}</span>{" "}
                <span className="break-all">{d.sha256}</span>
              </p>
            ))}
        </div>
      )}
    </Section>
  );
}

/** Slide 8: free for people, flat fees for professionals, never per client. */
function Pricing() {
  const { t } = useI18n();
  const contact = process.env.NEXT_PUBLIC_CONTACT_EMAIL;
  const contactHref = contact ? `mailto:${contact}` : "#for-lawyers";
  const plans: {
    key: string;
    name: string;
    price: string;
    body: string;
    cta: { label: string; href: string };
    highlight?: boolean;
  }[] = [
    {
      key: "people",
      name: t("price.people"),
      price: t("price.peoplePrice"),
      body: t("price.peopleBody"),
      cta: { label: t("price.peopleCta"), href: "/login" },
      highlight: true,
    },
    {
      key: "firms",
      name: t("price.firms"),
      price: t("price.firmsPrice"),
      body: t("price.firmsBody"),
      cta: { label: t("price.firmsCta"), href: "/lawyer/register" },
    },
    {
      key: "unis",
      name: t("price.unis"),
      price: t("price.unisPrice"),
      body: t("price.unisBody"),
      cta: { label: t("price.contact"), href: contactHref },
    },
    {
      key: "white",
      name: t("price.white"),
      price: t("price.whitePrice"),
      body: t("price.whiteBody"),
      cta: { label: t("price.contact"), href: contactHref },
    },
  ];

  return (
    <Section id="pricing" title={t("price.title")} lead={t("price.lead")}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((plan) => (
          <Card
            key={plan.key}
            className={
              plan.highlight
                ? "flex flex-col border-brand ring-1 ring-brand/30"
                : "flex flex-col"
            }
          >
            <h3 className="font-semibold text-slate-800">{plan.name}</h3>
            <p className="mt-1 text-lg font-semibold text-brand-700">{plan.price}</p>
            <p className="mt-2 flex-1 text-sm text-slate-600">{plan.body}</p>
            <div className="mt-4">
              <Link href={plan.cta.href}>
                <Button variant={plan.highlight ? "primary" : "secondary"}>
                  {plan.cta.label}
                </Button>
              </Link>
            </div>
          </Card>
        ))}
      </div>
    </Section>
  );
}

/** Slide 12: real lawyers, data that stays in Germany. */
function Trust() {
  const { t } = useI18n();
  const items = [
    { title: t("trust.verifiedTitle"), body: t("trust.verifiedBody") },
    { title: t("trust.dataTitle"), body: t("trust.dataBody") },
    { title: t("trust.offlineTitle"), body: t("trust.offlineBody") },
  ];
  return (
    <Section id="trust" title={t("trust.title")}>
      <div className="grid gap-4 sm:grid-cols-3">
        {items.map((item) => (
          <Card key={item.title}>
            <h3 className="font-semibold text-slate-800">{item.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{item.body}</p>
          </Card>
        ))}
      </div>
    </Section>
  );
}

/** Take it along: install on the phone, with an assistant that also works
 *  without a connection. */
function MobileApp() {
  const { t } = useI18n();
  return (
    <Section id="app" title={t("app.title")} lead={t("app.body")}>
      <InstallApp />
    </Section>
  );
}

/** The lawyers' door. They get an account and a portal of their own. */
function ForLawyers() {
  const { t } = useI18n();
  const { user } = useAuth();
  const points = [t("lp.auth.point1"), t("lp.auth.point2"), t("lp.auth.point3")];
  return (
    <Section id="for-lawyers" title={t("home.lawyerSignupTitle")} lead={t("lp.auth.heroBody")}>
      <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white">
        <ul className="flex flex-col gap-2 text-sm text-slate-200">
          {points.map((p) => (
            <li key={p} className="flex gap-2">
              <span aria-hidden className="text-brand-300">
                ✓
              </span>
              {p}
            </li>
          ))}
        </ul>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          {user?.role === "lawyer" ? (
            <Link href="/lawyer">
              <Button>{t("nav.lawyerPortal")}</Button>
            </Link>
          ) : (
            <>
              <Link href="/lawyer/register">
                <Button>{t("lp.auth.registerCta")}</Button>
              </Link>
              <Link href="/lawyer/login" className="text-sm text-slate-300 underline">
                {t("lp.auth.haveAccount")}
              </Link>
            </>
          )}
        </div>
      </Card>
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
      <MobileApp />
      <Offline />
      <Trust />
      <Pricing />
      <ForLawyers />
      <footer className="border-t border-slate-200/70 py-8 text-xs leading-relaxed text-slate-400">
        {t("common.disclaimer")}
      </footer>
    </main>
  );
}
