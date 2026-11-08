"use client";

// "Polite, firm German": describe the problem in your own language, get a
// formal German letter plus a translation, attach photos as evidence, and
// download it as a PDF with the photos as Anlagen. One model call per draft.

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type DocumentMeta, type ReplyDraft } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Field, Input, Select, Spinner, Textarea } from "@/components/ui";

const IMAGE = /^image\//;

export default function LettersPage() {
  const { user, loading } = useRequireAuth();
  const { t } = useI18n();
  const [files, setFiles] = useState<DocumentMeta[] | null>(null);
  const [situation, setSituation] = useState("");
  const [recipient, setRecipient] = useState("");
  const [replyTo, setReplyTo] = useState("");
  const [evidence, setEvidence] = useState<number[]>([]);
  const [draft, setDraft] = useState<ReplyDraft | null>(null);
  const [german, setGerman] = useState("");
  const [busy, setBusy] = useState<"draft" | "pdf" | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) api.listFiles().then(setFiles).catch(() => setFiles([]));
  }, [user]);

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    setBusy("draft");
    setError(null);
    try {
      const res = await api.draftReply({
        situation,
        recipient: recipient.trim() || undefined,
        reply_to_document_id: replyTo ? Number(replyTo) : undefined,
        evidence_document_ids: evidence,
      });
      setDraft(res);
      setGerman(res.german);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function download() {
    if (!draft) return;
    setBusy("pdf");
    setError(null);
    try {
      await api.downloadReplyPdf({
        subject: draft.subject,
        german,
        evidence_document_ids: draft.evidence.map((d) => d.id),
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (loading || !user)
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        {loading && <Spinner label={t("common.loading")} />}
      </div>
    );

  const toggle = (id: number) =>
    setEvidence((list) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]));

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-5 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t("letters.title")}</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">{t("letters.lead")}</p>
      </div>

      <Card>
        <form onSubmit={generate} className="flex flex-col gap-4">
          <Field label={t("letters.situation")}>
            <Textarea
              value={situation}
              onChange={(e) => setSituation(e.target.value)}
              placeholder={t("letters.situationPlaceholder")}
              minLength={10}
              maxLength={6000}
              required
              className="min-h-[120px]"
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("letters.recipient")}>
              <Input
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder={t("letters.recipientPlaceholder")}
                maxLength={255}
              />
            </Field>
            <Field label={t("letters.replyTo")}>
              <Select value={replyTo} onChange={(e) => setReplyTo(e.target.value)}>
                <option value="">{t("letters.none")}</option>
                {files
                  ?.filter((f) => !IMAGE.test(f.mime) || f.has_extracted_text)
                  .map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.filename}
                    </option>
                  ))}
              </Select>
            </Field>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium text-slate-600">{t("letters.evidence")}</p>
            {files === null ? (
              <Spinner />
            ) : files.length === 0 ? (
              <p className="text-sm text-slate-500">
                <Link href="/files" className="text-brand underline">
                  {t("letters.noFiles")}
                </Link>
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {files.map((f) => (
                  <label
                    key={f.id}
                    className={
                      "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm " +
                      (evidence.includes(f.id)
                        ? "border-brand bg-brand-50 text-brand-700"
                        : "border-slate-200 text-slate-600")
                    }
                  >
                    <input
                      type="checkbox"
                      checked={evidence.includes(f.id)}
                      onChange={() => toggle(f.id)}
                      disabled={!evidence.includes(f.id) && evidence.length >= 10}
                    />
                    {IMAGE.test(f.mime) ? "📷 " : "📄 "}
                    {f.filename}
                  </label>
                ))}
              </div>
            )}
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div>
            <Button type="submit" disabled={busy !== null || situation.trim().length < 10}>
              {busy === "draft" ? t("letters.generating") : t("letters.generate")}
            </Button>
          </div>
        </form>
      </Card>

      {draft && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h2 className="font-semibold text-slate-900">{t("letters.german")}</h2>
              <Button
                variant="ghost"
                onClick={() => {
                  void navigator.clipboard.writeText(german);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? t("letters.copied") : t("letters.copy")}
              </Button>
            </div>
            <p className="mb-2 text-sm font-medium text-slate-700">Betreff: {draft.subject}</p>
            <Textarea
              value={german}
              onChange={(e) => setGerman(e.target.value)}
              maxHeightPx={600}
              className="min-h-[320px] font-serif"
              lang="de"
            />
            {draft.evidence.length > 0 && (
              <ol className="mt-3 list-decimal ps-5 text-xs text-slate-500">
                {draft.evidence.map((d) => (
                  <li key={d.id}>Anlage: {d.filename}</li>
                ))}
              </ol>
            )}
            <div className="mt-3">
              <Button onClick={download} disabled={busy !== null || !german.trim()}>
                {busy === "pdf" ? t("lp.sending") : t("letters.download")}
              </Button>
            </div>
          </Card>
          <Card>
            <h2 className="mb-2 font-semibold text-slate-900">{t("letters.translation")}</h2>
            <p
              className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700"
              dir={draft.language === "ar" ? "rtl" : undefined}
            >
              {draft.translation}
            </p>
          </Card>
        </div>
      )}
      <p className="text-xs text-slate-400">{t("letters.disclaimer")}</p>
    </main>
  );
}
