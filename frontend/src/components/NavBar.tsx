"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { api, type Language } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { isLangCode } from "@/lib/translations";

function LanguageSwitcher() {
  const { user, refresh } = useAuth();
  const { lang, setLang, t } = useI18n();
  const [languages, setLanguages] = useState<Language[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.languages().then(setLanguages).catch(() => {});
  }, []);

  if (!user || languages.length === 0) return null;

  async function onChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const next = e.target.value;
    // Switch the UI immediately; don't wait on the network round trip.
    if (isLangCode(next)) setLang(next);
    setSaving(true);
    try {
      await api.updateMe({ language: next });
      await refresh();
    } finally {
      setSaving(false);
    }
  }

  return (
    <select
      value={lang}
      onChange={onChange}
      disabled={saving}
      title={t("nav.langSwitcherTitle")}
      className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-600 outline-none transition-shadow focus:border-brand focus:ring-2 focus:ring-brand/20"
    >
      {languages.map((l) => (
        <option key={l.code} value={l.code}>
          {l.name}
        </option>
      ))}
    </select>
  );
}

export function NavBar() {
  const { user, signOut } = useAuth();
  const { t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();

  // Lawyers and clients each get their own navigation; an admin sees the
  // client side plus the admin pages.
  const isLawyer = user?.role === "lawyer";
  const onLawyerSide = isLawyer || (!user && pathname.startsWith("/lawyer"));
  const LINKS = isLawyer
    ? [{ href: "/lawyer", label: t("nav.lawyerPortal") }]
    : [
        { href: "/dashboard", label: t("nav.dashboard") },
        { href: "/chat", label: t("nav.chat") },
        { href: "/timeline", label: t("nav.timeline") },
        { href: "/files", label: t("nav.files") },
        { href: "/lawyers", label: t("nav.lawyers") },
        { href: "/requests", label: t("nav.requests") },
        ...(user?.role === "admin" ? [{ href: "/admin", label: "Admin" }] : []),
      ];
  const isActive = (href: string) =>
    pathname === href || (href === "/admin" && pathname.startsWith("/admin"));

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/80 backdrop-blur-sm">
      <nav className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-6 py-3">
        <Link
          href={isLawyer ? "/lawyer" : "/"}
          className="flex shrink-0 items-center gap-2 text-lg font-bold tracking-tight text-slate-900"
        >
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-brand" />
          Francesca
          {onLawyerSide && (
            <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
              {t("nav.forLawyers")}
            </span>
          )}
        </Link>
        {user && (
          // Scrolls sideways on a phone instead of wrapping or overflowing.
          <div className="flex min-w-0 items-center gap-1 overflow-x-auto">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={clsx(
                  "shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                  isActive(l.href)
                    ? "bg-brand text-white shadow-soft"
                    : "text-slate-600 hover:bg-slate-100",
                )}
              >
                {l.label}
              </Link>
            ))}
            <LanguageSwitcher />
            <button
              onClick={() => {
                signOut();
                router.push(isLawyer ? "/lawyer/login" : "/login");
              }}
              className="ms-2 shrink-0 rounded-lg px-3 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              {t("nav.signOut")}
            </button>
          </div>
        )}
        {!user && (
          <div className="flex items-center gap-1">
            {onLawyerSide ? (
              <Link
                href="/"
                className="rounded-lg px-3 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100"
              >
                {t("nav.forClients")}
              </Link>
            ) : (
              <Link
                href="/lawyer/register"
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
              >
                {t("nav.areYouLawyer")}
              </Link>
            )}
            <Link
              href={onLawyerSide ? "/lawyer/login" : "/login"}
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-brand transition-colors hover:bg-brand-50"
            >
              {t("nav.login")}
            </Link>
          </div>
        )}
      </nav>
    </header>
  );
}
