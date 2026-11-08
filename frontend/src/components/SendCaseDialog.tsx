"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type CaseItem, type Conversation, type Lawyer } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button, Field, Modal, Select, Spinner, Textarea } from "@/components/ui";

/** Send a prepared case to one lawyer. The client picks a summary they
 *  already have, or a conversation to build one from, and adds a note. */
export function SendCaseDialog({ lawyer, onClose }: { lawyer: Lawyer; onClose: () => void }) {
  const { t, locale } = useI18n();
  const [cases, setCases] = useState<CaseItem[] | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  // "case:<id>", "conv:<id>" or "" (message only).
  const [source, setSource] = useState("");
  const [message, setMessage] = useState("");
  const [consent, setConsent] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.listCases(), api.listConversations()])
      .then(([c, conv]) => {
        setCases(c);
        setConversations(conv);
        // Default to the most recent thing they prepared.
        if (c.length > 0) setSource(`case:${c[0].id}`);
        else if (conv.length > 0) setSource(`conv:${conv[0].id}`);
      })
      .catch(() => setCases([]));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(null);
    const [kind, id] = source.split(":");
    try {
      await api.sendCase({
        lawyer_id: lawyer.id,
        case_id: kind === "case" ? Number(id) : undefined,
        conversation_id: kind === "conv" ? Number(id) : undefined,
        message: message.trim() || undefined,
        consent,
      });
      setSent(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  const nothingPrepared = cases !== null && cases.length === 0 && conversations.length === 0;

  return (
    <Modal title={t("req.sendTitle", { name: lawyer.name })} onClose={onClose}>
      {sent ? (
        <div className="flex flex-col items-start gap-4">
          <p className="text-sm text-green-700">{t("req.sent", { name: lawyer.name })}</p>
          <div className="flex gap-2">
            <Link href="/requests">
              <Button>{t("req.viewRequests")}</Button>
            </Link>
            <Button variant="ghost" onClick={onClose}>
              {t("lp.close")}
            </Button>
          </div>
        </div>
      ) : cases === null ? (
        <Spinner label={t("common.loading")} />
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <p className="text-sm text-slate-500">{t("req.sendLead")}</p>
          <Field
            label={t("req.whatToSend")}
            hint={source.startsWith("conv:") ? t("req.convHint") : undefined}
          >
            <Select value={source} onChange={(e) => setSource(e.target.value)}>
              {cases.length > 0 && (
                <optgroup label={t("req.groupCases")}>
                  {cases.map((c) => (
                    <option key={c.id} value={`case:${c.id}`}>
                      {c.title} · {new Date(c.created_at).toLocaleDateString(locale)}
                    </option>
                  ))}
                </optgroup>
              )}
              {conversations.length > 0 && (
                <optgroup label={t("req.groupConversations")}>
                  {conversations.map((c) => (
                    <option key={c.id} value={`conv:${c.id}`}>
                      {c.title}
                    </option>
                  ))}
                </optgroup>
              )}
              <option value="">{t("req.messageOnly")}</option>
            </Select>
          </Field>
          {nothingPrepared && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
              {t("req.nothingPrepared")}{" "}
              <Link href="/chat" className="font-medium underline">
                {t("home.openChat")}
              </Link>
            </p>
          )}
          <Field label={t("req.message")}>
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              maxLength={2000}
              required={!source}
              placeholder={t("req.messagePlaceholder")}
              className="min-h-[96px]"
            />
          </Field>
          <p className="text-xs text-slate-400">{t("req.privacyNote")}</p>
          {/* Per-case consent: nothing reaches this lawyer without it. */}
          <label className="flex items-start gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-700">
            <input
              type="checkbox"
              className="mt-0.5"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              required
            />
            {t("req.consent", { name: lawyer.name })}
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={sending || !consent}>
              {sending ? t("lp.sending") : t("req.send")}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              {t("timeline.cancel")}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
