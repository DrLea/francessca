"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type DashboardData } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { Card, ProgressBar, Spinner } from "@/components/ui";

const TILES: { key: keyof DashboardData; label: string; href: string }[] = [
  { key: "conversations", label: "Conversations", href: "/chat" },
  { key: "documents", label: "Documents", href: "/files" },
  { key: "cases", label: "Cases", href: "/chat" },
  { key: "exports", label: "Exports", href: "/chat" },
];

export default function DashboardPage() {
  const { user, loading } = useRequireAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api.dashboard().then(setData).catch((e) => setError(e.message));
  }, [user]);

  if (loading || !user) return <Centered>{loading && <Spinner label="Loading…" />}</Centered>;

  const limit = data?.token_limit ?? null;
  const used = data?.tokens_used ?? user.tokens_used;

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="mb-1 text-2xl font-semibold">
        Welcome{user.full_name ? `, ${user.full_name}` : ""}
      </h1>
      <p className="mb-6 text-sm text-slate-500">{user.email}</p>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {TILES.map((t) => (
          <Link key={t.key} href={t.href}>
            <Card className="text-center transition hover:shadow-md">
              <div className="text-3xl font-bold text-brand">
                {data ? data[t.key] : "—"}
              </div>
              <div className="text-sm text-slate-500">{t.label}</div>
            </Card>
          </Link>
        ))}
      </div>

      <Card className="mt-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-semibold">Token usage</h2>
          <span className="text-sm text-slate-500">
            {used.toLocaleString()}
            {limit !== null ? ` / ${limit.toLocaleString()}` : " (unlimited)"}
          </span>
        </div>
        {limit !== null ? (
          <ProgressBar value={used} max={limit} />
        ) : (
          <p className="text-sm text-slate-500">Premium plan — no monthly limit.</p>
        )}
      </Card>
    </main>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-[40vh] items-center justify-center">{children}</div>;
}
