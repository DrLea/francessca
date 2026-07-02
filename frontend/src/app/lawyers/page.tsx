"use client";

import { useState } from "react";
import { api, type Lawyer } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { Badge, Button, Card, Input, Spinner } from "@/components/ui";

export default function LawyersPage() {
  const { user, loading } = useRequireAuth();
  const [specialization, setSpecialization] = useState("");
  const [city, setCity] = useState("");
  const [language, setLanguage] = useState("");
  const [results, setResults] = useState<Lawyer[]>([]);
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        {loading && <Spinner label="Loading…" />}
      </div>
    );

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
      <h1 className="text-2xl font-semibold">Find a lawyer</h1>
      <form onSubmit={search} className="grid grid-cols-1 gap-2 sm:grid-cols-4">
        <Input
          placeholder="Specialization"
          value={specialization}
          onChange={(e) => setSpecialization(e.target.value)}
        />
        <Input placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
        <Input
          placeholder="Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        />
        <Button type="submit" disabled={busy}>
          {busy ? "Searching…" : "Search"}
        </Button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col gap-3">
        {results.map((lw) => (
          <Card key={lw.id}>
            <div className="flex items-baseline justify-between">
              <h2 className="font-semibold">{lw.name}</h2>
              <span className="text-sm text-slate-500">{lw.city}</span>
            </div>
            {lw.law_firm && <p className="text-sm text-slate-600">{lw.law_firm}</p>}
            {lw.address && <p className="text-xs text-slate-400">{lw.address}</p>}
            <div className="mt-2 flex flex-wrap gap-1">
              {lw.specializations.map((s) => (
                <Badge key={s}>{s}</Badge>
              ))}
            </div>
            {lw.languages.length > 0 && (
              <p className="mt-1 text-xs text-slate-500">
                Languages: {lw.languages.join(", ")}
              </p>
            )}
            <div className="mt-2 flex gap-4 text-sm">
              {lw.email && (
                <a className="text-brand underline" href={`mailto:${lw.email}`}>
                  Email
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
                  Website
                </a>
              )}
            </div>
          </Card>
        ))}
        {searched && results.length === 0 && (
          <p className="text-sm text-slate-400">No lawyers matched your search.</p>
        )}
      </div>
    </main>
  );
}
