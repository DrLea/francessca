"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type ClarifyAnswer,
  type Conversation,
  type DocumentMeta,
  type Message,
} from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Disclaimer, Spinner, Textarea } from "@/components/ui";
import { ClarifyPrompt } from "@/components/ClarifyPrompt";
import { Markdown } from "@/components/Markdown";
import clsx from "clsx";

// Which conversation the user had open, so switching to Timeline or
// Documents and back doesn't drop them into an empty chat.
const ACTIVE_KEY = "francessca_active_conversation";
// ...and how far down it they had scrolled, per conversation.
const SCROLL_KEY = "francessca_chat_scroll";
// Sentinel meaning "pin to the newest message" rather than a pixel offset.
const BOTTOM = -1;

function readScrollMap(): Record<string, number> {
  try {
    return JSON.parse(window.localStorage.getItem(SCROLL_KEY) ?? "{}");
  } catch {
    return {};
  }
}

export default function ChatPage() {
  const { user, loading } = useRequireAuth();
  const { t, locale } = useI18n();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | undefined>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Where to put the scroll position once the next render has painted:
  // a remembered offset, BOTTOM, or null for "leave it alone".
  const pendingScroll = useRef<number | null>(null);
  const scrollSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Questions are pending only while the assistant's question turn is the
  // last thing in the transcript — answering (or typing anything) pushes new
  // messages on top and retires them.
  const lastMessage = messages[messages.length - 1];
  const pending =
    lastMessage?.role === "assistant" && lastMessage.questions?.length
      ? lastMessage
      : null;

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

  // Reopen whatever the user was reading: an explicit deep link from a
  // timeline entry (/chat?c=<id>) wins, otherwise the conversation they had
  // open before navigating to another tab. Read from location rather than
  // useSearchParams so the page still prerenders without a Suspense boundary.
  useEffect(() => {
    if (!user) return;
    const fromLink = Number(new URLSearchParams(window.location.search).get("c"));
    const remembered = Number(window.localStorage.getItem(ACTIVE_KEY) ?? 0);
    const id = fromLink || remembered;
    if (id) {
      openConversation(id).catch(() => window.localStorage.removeItem(ACTIVE_KEY));
    }
    // Once only, on arrival.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  useEffect(() => {
    if (activeId) window.localStorage.setItem(ACTIVE_KEY, String(activeId));
  }, [activeId]);

  async function openConversation(id: number) {
    setActiveId(id);
    setExportMsg(null);
    const detail = await api.getConversation(id);
    // Come back exactly where they left off; a conversation they have never
    // opened starts at the newest message.
    pendingScroll.current = readScrollMap()[String(id)] ?? BOTTOM;
    setMessages(detail.messages);
  }

  // Apply the queued scroll position after the messages have rendered.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || pendingScroll.current === null) return;
    el.scrollTop =
      pendingScroll.current === BOTTOM ? el.scrollHeight : pendingScroll.current;
    pendingScroll.current = null;
  }, [messages]);

  function onMessagesScroll() {
    const el = scrollRef.current;
    if (!el || !activeId) return;
    // Throttled: scrolling fires constantly and this touches localStorage.
    if (scrollSaveTimer.current) clearTimeout(scrollSaveTimer.current);
    const top = el.scrollTop;
    scrollSaveTimer.current = setTimeout(() => {
      const map = readScrollMap();
      map[String(activeId)] = top;
      window.localStorage.setItem(SCROLL_KEY, JSON.stringify(map));
    }, 250);
  }

  function newConversation() {
    window.localStorage.removeItem(ACTIVE_KEY);
    setActiveId(undefined);
    setMessages([]);
    setExportMsg(null);
  }

  /** One turn = one request = one model call, whether it carries typed text,
   *  a batch of answers to clarifying questions, or both. */
  async function sendTurn(
    payload: { message?: string; answers?: ClarifyAnswer[] },
    optimisticId?: number,
  ) {
    setBusy(true);
    setError(null);
    try {
      const res = await api.sendMessage({
        conversation_id: activeId,
        document_ids: attached,
        ...payload,
      });
      setActiveId(res.conversation_id);
      pendingScroll.current = BOTTOM;
      setMessages((m) => [
        // Swap the local echo for the message the server actually stored.
        ...m.filter((x) => x.id !== optimisticId),
        res.user_message,
        res.message,
      ]);
      if (!activeId) loadConversations();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    const text = input;
    setInput("");
    const optimisticId = -Date.now();
    pendingScroll.current = BOTTOM;
    setMessages((m) => [
      ...m,
      { id: optimisticId, role: "user", content: text, token_count: 0, created_at: "" },
    ]);
    await sendTurn({ message: text }, optimisticId);
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
          {/* Francesca is free for people: no allowance to show. */}
          <span />
          {activeId && (
            <Button onClick={exportCase} disabled={exporting} variant="ghost">
              {exporting ? t("chat.generating") : t("chat.exportPdf")}
            </Button>
          )}
        </div>
        {exportMsg && <p className="text-sm text-green-600">{exportMsg}</p>}

        {/* Its own scroll container, so the position can be restored and new
            messages don't push the page around. */}
        <div
          ref={scrollRef}
          onScroll={onMessagesScroll}
          className="flex h-[60vh] flex-col gap-3 overflow-y-auto rounded-xl border border-slate-200/80 bg-white p-6 shadow-soft"
        >
          {messages.length === 0 && (
            <p className="text-slate-500">{t("chat.emptyPrompt")}</p>
          )}
          {messages.map((m) => (
            m.content.trim() === "" ? null : (
            <div
              key={m.id}
              className={
                m.role === "user"
                  ? "max-w-[80%] self-end whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand px-4 py-2.5 text-sm text-white shadow-soft"
                  : "max-w-[80%] self-start rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-2.5 text-sm text-slate-800"
              }
            >
              {/* The model writes markdown; the user's own text is shown verbatim. */}
              {m.role === "user" ? m.content : <Markdown text={m.content} />}
            </div>
            )
          ))}
          {busy && <Spinner label={t("chat.typing")} />}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        {/* Clarifying questions from the latest reply, asked one at a time.
            Keyed by message id so a new set starts from the first question. */}
        {pending && (
          <ClarifyPrompt
            key={pending.id}
            questions={pending.questions ?? []}
            disabled={busy}
            onSubmit={(answers) => sendTurn({ answers })}
          />
        )}

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
