"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Partner, type PartnerKind } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AdminShell, fmtDate } from "@/components/AdminShell";
import { Button, Card, Field, Input, Select, Spinner, StatusPill } from "@/components/ui";

const KINDS: Record<PartnerKind, string> = {
  university: "University",
  law_clinic: "Law Clinic",
  international_office: "International office",
  ngo: "NGO",
  integration_office: "Integration office",
};

/** Universities, Law Clinics and NGOs with a partner licence (€500/month).
 *  No payment provider: record payments by extending paid-until. */
export default function AdminPartnersPage() {
  const { user } = useAuth();
  const [partners, setPartners] = useState<Partner[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    kind: "law_clinic" as PartnerKind,
    city: "",
    contact_name: "",
    contact_email: "",
  });

  const load = useCallback(() => {
    api.adminPartners().then(setPartners).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (user?.role === "admin") load();
  }, [user, load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.adminCreatePartner({
        name: form.name,
        kind: form.kind,
        city: form.city || undefined,
        contact_name: form.contact_name || undefined,
        contact_email: form.contact_email || undefined,
      });
      setForm({ name: "", kind: "law_clinic", city: "", contact_name: "", contact_email: "" });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function update(p: Partner, body: Parameters<typeof api.adminUpdatePartner>[1]) {
    setError(null);
    try {
      const updated = await api.adminUpdatePartner(p.id, body);
      setPartners((list) => (list ?? []).map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <AdminShell
      title="Partners"
      lead="Universities, Law Clinics and international offices with a partner licence. Link a lawyer account to a partner on the Lawyers page."
    >
      <Card>
        <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
          <Field label="Name">
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              minLength={2}
            />
          </Field>
          <Field label="Kind">
            <Select
              value={form.kind}
              onChange={(e) => setForm({ ...form, kind: e.target.value as PartnerKind })}
            >
              {Object.entries(KINDS).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="City">
            <Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </Field>
          <Field label="Contact person">
            <Input
              value={form.contact_name}
              onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
            />
          </Field>
          <Field label="Contact email">
            <Input
              type="email"
              value={form.contact_email}
              onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
            />
          </Field>
          <div className="flex items-end">
            <Button type="submit">Add partner</Button>
          </div>
        </form>
      </Card>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!partners && !error && <Spinner label="Loading…" />}
      {partners?.length === 0 && <Card className="text-sm text-slate-500">No partners yet.</Card>}
      {partners?.map((p) => (
        <Card key={p.id} className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold text-slate-900">{p.name}</h3>
              <p className="text-sm text-slate-500">
                {[KINDS[p.kind], p.city, p.contact_name, p.contact_email].filter(Boolean).join(" · ")}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                €{Number(p.monthly_fee).toFixed(0)} / month · paid until{" "}
                {p.paid_until ? fmtDate(p.paid_until) : "—"}
              </p>
            </div>
            <StatusPill status={p.status === "active" ? "approved" : p.status === "trial" ? "pending" : "declined"} label={p.status} />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button onClick={() => update(p, { extend_paid_months: 1 })}>Record payment: +1 month</Button>
            <Button variant="ghost" onClick={() => update(p, { extend_paid_months: 12 })}>
              +12 months
            </Button>
            {p.status !== "inactive" ? (
              <Button variant="ghost" onClick={() => update(p, { status: "inactive" })}>
                Deactivate
              </Button>
            ) : (
              <Button variant="ghost" onClick={() => update(p, { status: "trial" })}>
                Reactivate
              </Button>
            )}
          </div>
        </Card>
      ))}
    </AdminShell>
  );
}
