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

  const LINKS = [
    { href: "/dashboard", label: t("nav.dashboard") },
    { href: "/chat", label: t("nav.chat") },
    { href: "/timeline", label: t("nav.timeline") },
    { href: "/files", label: t("nav.files") },
    { href: "/lawyers", label: t("nav.lawyers") },
  ];

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/80 backdrop-blur-sm">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link
          href="/"
          className="flex items-center gap-2 text-lg font-bold tracking-tight text-slate-900"
        >
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-brand" />
          Francessca
        </Link>
        {user && (
          <div className="flex items-center gap-1">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={clsx(
                  "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                  pathname === l.href
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
                router.push("/login");
              }}
              className="ms-2 rounded-lg px-3 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              {t("nav.signOut")}
            </button>
          </div>
        )}
        {!user && (
          <Link
            href="/login"
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-brand transition-colors hover:bg-brand-50"
          >
            {t("nav.login")}
          </Link>
        )}
      </nav>
    </header>
  );
}
