"use client";

import { useState } from "react";
import { api, type Lawyer } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useT } from "@/lib/i18n";
import { SendCaseDialog } from "@/components/SendCaseDialog";
import { Badge, Button, Card, Input, Spinner, Stars } from "@/components/ui";

export default function LawyersPage() {
  const { user, loading } = useRequireAuth();
  const t = useT();
  const [specialization, setSpecialization] = useState("");
  const [city, setCity] = useState("");
  const [language, setLanguage] = useState("");
  const [results, setResults] = useState<Lawyer[]>([]);
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sendTo, setSendTo] = useState<Lawyer | null>(null);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api.searchLawyers({ specialization, city, language });
      setResults(res.items);
      setSearched(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
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
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t("lawyers.title")}</h1>
      <form onSubmit={search} className="grid grid-cols-1 gap-2 sm:grid-cols-4">
        <Input
          placeholder={t("lawyers.specialization")}
          value={specialization}
          onChange={(e) => setSpecialization(e.target.value)}
        />
        <Input
          placeholder={t("lawyers.city")}
          value={city}
          onChange={(e) => setCity(e.target.value)}
        />
        <Input
          placeholder={t("lawyers.language")}
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        />
        <Button type="submit" disabled={busy}>
          {busy ? t("lawyers.searching") : t("lawyers.search")}
        </Button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col gap-3">
        {results.map((lw) => (
          <Card key={lw.id} className="transition-shadow hover:shadow-lg">
            <div className="flex items-baseline justify-between">
              <h2 className="font-semibold text-slate-900">{lw.name}</h2>
              <span className="text-sm text-slate-500">{lw.city}</span>
            </div>
            {lw.law_firm && <p className="text-sm text-slate-600">{lw.law_firm}</p>}
            {!!lw.rating_count && lw.rating_avg != null && (
              <p className="flex items-center gap-1.5 text-xs text-slate-500">
                <Stars value={lw.rating_avg} size="text-sm" />
                {lw.rating_avg.toFixed(1)} · {t("req.reviewCount", { count: lw.rating_count })}
              </p>
            )}
            {lw.bio && (
              <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-slate-600">{lw.bio}</p>
            )}
            {(lw.years_experience != null || lw.consultation_fee || lw.office_hours) && (
              <p className="mt-1 text-xs text-slate-500">
                {[
                  lw.years_experience != null
                    ? t("req.years", { count: lw.years_experience })
                    : null,
                  lw.consultation_fee,
                  lw.office_hours,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}
            {lw.address && <p className="text-xs text-slate-400">{lw.address}</p>}
            <div className="mt-2 flex flex-wrap gap-1">
              {lw.specializations.map((s) => (
                <Badge key={s}>{s}</Badge>
              ))}
            </div>
            {lw.languages.length > 0 && (
              <p className="mt-1 text-xs text-slate-500">
                {t("lawyers.languagesLabel", { list: lw.languages.join(", ") })}
              </p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-4 text-sm">
              {lw.accepts_requests && (
                <Button onClick={() => setSendTo(lw)}>{t("req.sendCta")}</Button>
              )}
              {lw.email && (
                <a className="text-brand underline" href={`mailto:${lw.email}`}>
                  {t("lawyers.email")}
                </a>
              )}
              {lw.phone && (
                <a className="text-brand underline" href={`tel:${lw.phone}`}>
                  {lw.phone}
                </a>
              )}
              {lw.website && (
                <a
                  className="text-brand underline"
                  href={lw.website}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("lawyers.website")}
                </a>
              )}
            </div>
          </Card>
        ))}
        {searched && results.length === 0 && (
          <p className="text-sm text-slate-400">{t("lawyers.noResults")}</p>
        )}
      </div>
      {sendTo && <SendCaseDialog lawyer={sendTo} onClose={() => setSendTo(null)} />}
    </main>
  );
}
