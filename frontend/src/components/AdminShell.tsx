"use client";

// The admin area is for the site owner only, so it is English-only — the
// rest of the app stays fully translated.

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useRequireRole } from "@/lib/auth";
import { Spinner } from "@/components/ui";

const PAGES = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/lawyers", label: "Lawyers" },
  { href: "/admin/feedback", label: "Feedback" },
];

export function AdminShell({
  title,
  lead,
  badges = {},
  children,
}: {
  title: string;
  lead?: string;
  /** Counts shown next to a page link, e.g. pending approvals. */
  badges?: Record<string, number>;
  children: React.ReactNode;
}) {
  const { user, loading } = useRequireRole("admin");
  const pathname = usePathname().replace(/\/$/, "") || "/";

  if (loading || !user)
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        {loading && <Spinner label="Loading…" />}
      </div>
    );

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-5 px-6 py-8">
      <div className="flex gap-1 border-b border-slate-200">
        {PAGES.map((page) => (
          <Link
            key={page.href}
            href={page.href}
            className={clsx(
              "-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              pathname === page.href
                ? "border-brand text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-800",
            )}
          >
            {page.label}
            {!!badges[page.href] && (
              <span className="rounded-full bg-amber-500 px-1.5 text-[11px] font-semibold text-white">
                {badges[page.href]}
              </span>
            )}
          </Link>
        ))}
      </div>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {lead && <p className="mt-1 text-sm text-slate-500">{lead}</p>}
      </div>
      {children}
    </main>
  );
}

export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

export const fmtMoney = (value: number) =>
  value.toLocaleString("en-GB", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
