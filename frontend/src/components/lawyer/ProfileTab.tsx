"use client";

import { useState } from "react";
import { api, type LawyerMe } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Field, Input, Textarea } from "@/components/ui";

const toList = (value: string) =>
  value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

/** The detailed profile editor — everything the short sign-up form left out. */
export function ProfileTab({ me, onSaved }: { me: LawyerMe; onSaved: (me: LawyerMe) => void }) {
  const { t } = useI18n();
  const p = me.profile;
  const [form, setForm] = useState({
    name: p.name,
    law_firm: p.law_firm ?? "",
    city: p.city ?? "",
    address: p.address ?? "",
    email: p.email ?? "",
    phone: p.phone ?? "",
    website: p.website ?? "",
    photo_url: p.photo_url ?? "",
    bio: p.bio ?? "",
    years_experience: p.years_experience != null ? String(p.years_experience) : "",
    consultation_fee: p.consultation_fee ?? "",
    office_hours: p.office_hours ?? "",
    specializations: p.specializations.join(", "),
    languages: p.languages.join(", "),
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set =
    (key: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setSaved(false);
      setForm((f) => ({ ...f, [key]: e.target.value }));
    };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const years = Number(form.years_experience);
      // Empty strings are sent as null so a field can be cleared.
      const text = (v: string) => v.trim() || null;
      onSaved(
        await api.updateLawyerProfile({
          name: form.name.trim(),
          law_firm: text(form.law_firm),
          city: text(form.city),
          address: text(form.address),
          email: text(form.email),
          phone: text(form.phone),
          website: text(form.website),
          photo_url: text(form.photo_url),
          bio: text(form.bio),
          years_experience:
            form.years_experience.trim() && Number.isFinite(years) ? Math.round(years) : null,
          consultation_fee: text(form.consultation_fee),
          office_hours: text(form.office_hours),
          specializations: toList(form.specializations),
          languages: toList(form.languages),
        }),
      );
      setSaved(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <Card>
        <h3 className="mb-4 font-semibold text-slate-900">{t("lp.profile.basics")}</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("lp.field.name")}>
            <Input required minLength={2} value={form.name} onChange={set("name")} />
          </Field>
          <Field label={t("lp.field.firm")}>
            <Input value={form.law_firm} onChange={set("law_firm")} />
          </Field>
          <Field label={t("lp.field.city")}>
            <Input value={form.city} onChange={set("city")} />
          </Field>
          <Field label={t("lp.field.address")}>
            <Input value={form.address} onChange={set("address")} />
          </Field>
        </div>
      </Card>

      <Card>
        <h3 className="mb-4 font-semibold text-slate-900">{t("lp.profile.expertise")}</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("lp.field.specializations")} hint={t("lp.field.commaHint")}>
            <Input value={form.specializations} onChange={set("specializations")} />
          </Field>
          <Field label={t("lp.field.languages")} hint={t("lp.field.commaHint")}>
            <Input value={form.languages} onChange={set("languages")} />
          </Field>
          <Field label={t("lp.field.years")}>
            <Input
              type="number"
              min={0}
              max={80}
              value={form.years_experience}
              onChange={set("years_experience")}
            />
          </Field>
          <Field label={t("lp.field.fee")} hint={t("lp.field.feeHint")}>
            <Input value={form.consultation_fee} onChange={set("consultation_fee")} />
          </Field>
        </div>
        <Field label={t("lp.field.bio")} hint={t("lp.field.bioHint")} className="mt-3">
          <Textarea
            value={form.bio}
            onChange={set("bio")}
            maxLength={4000}
            maxHeightPx={320}
            className="min-h-[120px]"
          />
        </Field>
      </Card>

      <Card>
        <h3 className="mb-1 font-semibold text-slate-900">{t("lp.profile.contact")}</h3>
        <p className="mb-4 text-xs text-slate-500">{t("lp.profile.contactHint")}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("lp.field.publicEmail")}>
            <Input type="email" value={form.email} onChange={set("email")} />
          </Field>
          <Field label={t("lp.field.phone")}>
            <Input value={form.phone} onChange={set("phone")} />
          </Field>
          <Field label={t("lp.field.website")}>
            <Input
              type="url"
              placeholder="https://"
              value={form.website}
              onChange={set("website")}
            />
          </Field>
          <Field label={t("lp.field.hours")}>
            <Input
              placeholder="Mo–Fr 9–17"
              value={form.office_hours}
              onChange={set("office_hours")}
            />
          </Field>
          <Field label={t("lp.field.photo")} className="sm:col-span-2">
            <Input
              type="url"
              placeholder="https://"
              value={form.photo_url}
              onChange={set("photo_url")}
            />
          </Field>
        </div>
      </Card>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={saving}>
          {saving ? t("timeline.saving") : t("lp.profile.save")}
        </Button>
        {saved && <span className="text-sm text-green-700">{t("lp.profile.saved")}</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </form>
  );
}
