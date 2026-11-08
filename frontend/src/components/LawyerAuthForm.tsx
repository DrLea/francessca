"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Field, Input } from "@/components/ui";

const list = (value: string) =>
  value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

/** Sign-in and sign-up for lawyers — their own door into the app, separate
 *  from the client login. Sign-up asks only for the essentials; the rest of
 *  the profile is filled in from the portal afterwards. */
export function LawyerAuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const { user, signIn, signOut } = useAuth();
  const { t, lang } = useI18n();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    city: "",
    law_firm: "",
    specializations: "",
    languages: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) router.replace(homeFor(user));
  }, [user, router]);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        const { access_token } = await api.registerLawyer({
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
          city: form.city.trim() || undefined,
          law_firm: form.law_firm.trim() || undefined,
          specializations: list(form.specializations),
          languages: list(form.languages),
          language: lang,
        });
        await signIn(access_token);
        router.push("/lawyer");
        return;
      }
      const { access_token } = await api.login({
        email: form.email.trim(),
        password: form.password,
      });
      // This door is for lawyers: a client account is turned away here
      // rather than silently dropped into the client app.
      setToken(access_token);
      const me = await api.me();
      if (me.role === "user") {
        setToken(null);
        signOut();
        setError(t("lp.auth.notLawyer"));
        return;
      }
      await signIn(getToken() ?? access_token);
      router.push(homeFor(me));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const register = mode === "register";

  return (
    <main className="mx-auto grid max-w-4xl gap-8 px-6 py-12 md:grid-cols-[1fr_1.1fr]">
      <div className="md:pt-6">
        <p className="mb-3 inline-block rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
          {t("lp.auth.badge")}
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          {t("lp.auth.heroTitle")}
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-600">{t("lp.auth.heroBody")}</p>
        <ul className="mt-5 flex flex-col gap-2 text-sm text-slate-600">
          {[t("lp.auth.point1"), t("lp.auth.point2"), t("lp.auth.point3")].map((p) => (
            <li key={p} className="flex gap-2">
              <span aria-hidden className="text-brand">
                ✓
              </span>
              {p}
            </li>
          ))}
        </ul>
      </div>

      <Card className="animate-fade-in">
        <h2 className="mb-4 text-xl font-semibold tracking-tight text-slate-900">
          {register ? t("lp.auth.registerTitle") : t("lp.auth.loginTitle")}
        </h2>
        <form onSubmit={submit} className="flex flex-col gap-3">
          {register && (
            <Field label={t("lp.field.name")}>
              <Input required minLength={2} value={form.name} onChange={set("name")} />
            </Field>
          )}
          <Field label={t("lp.field.email")}>
            <Input required type="email" value={form.email} onChange={set("email")} />
          </Field>
          <Field label={t("lp.field.password")}>
            <Input
              required
              type="password"
              minLength={8}
              value={form.password}
              onChange={set("password")}
            />
          </Field>
          {register && (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label={t("lp.field.city")}>
                  <Input value={form.city} onChange={set("city")} />
                </Field>
                <Field label={t("lp.field.firm")}>
                  <Input value={form.law_firm} onChange={set("law_firm")} />
                </Field>
              </div>
              <Field label={t("lp.field.specializations")} hint={t("lp.field.commaHint")}>
                <Input value={form.specializations} onChange={set("specializations")} />
              </Field>
              <p className="text-xs text-slate-400">{t("lp.auth.reviewNote")}</p>
            </>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={loading}>
            {loading
              ? t("login.pleaseWait")
              : register
                ? t("lp.auth.registerCta")
                : t("lp.auth.loginCta")}
          </Button>
        </form>
        <div className="mt-4 flex flex-col gap-1 text-sm">
          <Link
            className="text-brand underline"
            href={register ? "/lawyer/login" : "/lawyer/register"}
          >
            {register ? t("lp.auth.haveAccount") : t("lp.auth.needAccount")}
          </Link>
          <Link className="text-slate-500 underline" href="/login">
            {t("lp.auth.clientInstead")}
          </Link>
        </div>
      </Card>
    </main>
  );
}
