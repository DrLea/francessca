"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type Conversation,
  type DocumentMeta,
  type Message,
} from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Disclaimer, Spinner, Textarea } from "@/components/ui";
import clsx from "clsx";

export default function ChatPage() {
  const { user, loading } = useRequireAuth();
  const { t, locale } = useI18n();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | undefined>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [remaining, setRemaining] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // Document attachment
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [attached, setAttached] = useState<number[]>([]);

  // Case export
  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState<string | null>(null);

  const loadConversations = useCallback(() => {
    api.listConversations().then(setConversations).catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) return;
    loadConversations();
    api.listFiles().then(setDocs).catch(() => {});
  }, [user, loadConversations]);

  async function openConversation(id: number) {
    setActiveId(id);
    setExportMsg(null);
    const detail = await api.getConversation(id);
    setMessages(detail.messages);
  }

  function newConversation() {
    setActiveId(undefined);
    setMessages([]);
    setExportMsg(null);
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    const text = input;
    setInput("");
    setMessages((m) => [
      ...m,
      { id: Date.now(), role: "user", content: text, token_count: 0, created_at: "" },
    ]);
    setBusy(true);
    setError(null);
    try {
      const res = await api.sendMessage({
        conversation_id: activeId,
        message: text,
        document_ids: attached,
      });
      setActiveId(res.conversation_id);
      setRemaining(res.tokens_remaining);
      setMessages((m) => [...m, res.message]);
      if (!activeId) loadConversations();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function onComposerKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends the message; Shift+Enter (or Enter with an IME composing)
    // inserts a newline instead, matching familiar chat-app conventions.
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  async function exportCase() {
    if (!activeId) return;
    setExporting(true);
    setExportMsg(null);
    try {
      const res = await api.exportCase({
        conversation_id: activeId,
        include_documents: true,
      });
      await api.downloadExport(res.pdf_export_id, `case_${res.case_id}_summary.pdf`);
      setExportMsg(t("chat.exportDone"));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExporting(false);
    }
  }

  if (loading || !user)
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        {loading && <Spinner label={t("common.loading")} />}
      </div>
    );

  return (
    <main className="mx-auto grid max-w-5xl gap-4 px-6 py-8 md:grid-cols-[220px_1fr]">
      {/* Sidebar */}
      <aside className="flex flex-col gap-2">
        <Button onClick={newConversation} variant="secondary">
          {t("chat.newConversation")}
        </Button>
        <div className="flex flex-col gap-1">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => openConversation(c.id)}
              className={clsx(
                "truncate rounded-lg px-3 py-2 text-left text-sm transition-colors",
                activeId === c.id
                  ? "bg-brand text-white shadow-soft"
                  : "text-slate-600 hover:bg-slate-100",
              )}
            >
              {c.title}
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="px-1 text-xs text-slate-400">{t("chat.noConversations")}</p>
          )}
        </div>
      </aside>

      {/* Chat panel */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          {remaining !== null && (
            <span className="text-xs text-slate-500">
              {t("chat.tokensRemaining", { count: remaining.toLocaleString(locale) })}
            </span>
          )}
          {activeId && (
            <Button onClick={exportCase} disabled={exporting} variant="ghost">
              {exporting ? t("chat.generating") : t("chat.exportPdf")}
            </Button>
          )}
        </div>
        {exportMsg && <p className="text-sm text-green-600">{exportMsg}</p>}

        <Card className="flex min-h-[45vh] flex-col gap-3 overflow-y-auto">
          {messages.length === 0 && (
            <p className="text-slate-500">{t("chat.emptyPrompt")}</p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={
                m.role === "user"
                  ? "max-w-[80%] self-end whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand px-4 py-2.5 text-sm text-white shadow-soft"
                  : "max-w-[80%] self-start whitespace-pre-wrap rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-2.5 text-sm text-slate-800"
              }
            >
              {m.content}
            </div>
          ))}
          {busy && <Spinner label={t("chat.typing")} />}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </Card>

        {docs.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500">{t("chat.attachDocuments")}</span>
            {docs.map((d) => {
              const on = attached.includes(d.id);
              return (
                <button
                  key={d.id}
                  onClick={() =>
                    setAttached((a) =>
                      on ? a.filter((x) => x !== d.id) : [...a, d.id],
                    )
                  }
                  className={clsx(
                    "rounded-full border px-2.5 py-0.5 transition-colors",
                    on
                      ? "border-brand bg-brand/10 text-brand"
                      : "border-slate-300 text-slate-500 hover:border-slate-400",
                  )}
                >
                  {d.filename}
                </button>
              );
            })}
          </div>
        )}

        <form
          ref={formRef}
          onSubmit={send}
          className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-soft transition-shadow focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/20"
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onComposerKeyDown}
            placeholder={t("chat.typeMessage")}
            maxHeightPx={200}
            bare
          />
          <Button type="submit" disabled={busy || !input.trim()} className="shrink-0">
            {t("chat.send")}
          </Button>
        </form>
        <Disclaimer />
      </section>
    </main>
  );
}
