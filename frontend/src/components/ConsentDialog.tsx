"use client";

// Asks for consent to store case data on our servers in Germany. Opens
// whenever the API answers 428 (see request() in lib/api.ts), so every
// page that writes case data is covered without its own handling.

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Modal } from "@/components/ui";

export function ConsentDialog() {
  const { t } = useI18n();
  const { refresh } = useAuth();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener("francesca:consent-required", show);
    return () => window.removeEventListener("francesca:consent-required", show);
  }, []);

  if (!open) return null;

  async function agree() {
    setSaving(true);
    setError(null);
    try {
      await api.giveConsent();
      await refresh();
      setOpen(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={t("consent.title")} onClose={() => setOpen(false)}>
      <p className="text-sm leading-relaxed text-slate-600">{t("consent.body")}</p>
      <p className="mt-3 text-sm text-slate-500">{t("consent.offlineHint")}</p>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button onClick={agree} disabled={saving}>
          {t("consent.agree")}
        </Button>
        <Link href="/offline" onClick={() => setOpen(false)}>
          <Button variant="ghost">{t("consent.offline")}</Button>
        </Link>
      </div>
    </Modal>
  );
}
