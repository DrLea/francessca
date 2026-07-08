"use client";

import Link from "next/link";
import { Button, Card, Disclaimer } from "@/components/ui";
import { useT } from "@/lib/i18n";

export default function Home() {
  const t = useT();
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-8 px-6 py-20">
      <div className="flex flex-col gap-4 animate-fade-in">
        <h1 className="text-5xl font-bold tracking-tight text-slate-900">
          Franc<span className="text-brand">essca</span>
        </h1>
        <p className="text-lg leading-relaxed text-slate-600">{t("home.tagline")}</p>
      </div>
      <Card className="animate-fade-in">
        <div className="flex flex-wrap gap-3">
          <Link href="/login">
            <Button>{t("home.getStarted")}</Button>
          </Link>
          <Link href="/lawyers">
            <Button variant="secondary">{t("home.findLawyer")}</Button>
          </Link>
        </div>
        <Disclaimer />
      </Card>
    </main>
  );
}
