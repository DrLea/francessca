"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type Conversation,
  type DocumentMeta,
  type Message,
} from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { Button, Card, Disclaimer, Input, Spinner } from "@/components/ui";

export default function ChatPage() {
  const { user, loading } = useRequireAuth();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | undefined>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [remaining, setRemaining] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      setExportMsg("Case summary PDF downloaded.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExporting(false);
    }
  }

  if (loading || !user)
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        {loading && <Spinner label="Loading…" />}
      </div>
    );

  return (
    <main className="mx-auto grid max-w-5xl gap-4 px-6 py-8 md:grid-cols-[220px_1fr]">
      {/* Sidebar */}
      <aside className="flex flex-col gap-2">
        <Button onClick={newConversation} variant="secondary">
          + New conversation
        </Button>
        <div className="flex flex-col gap-1">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => openConversation(c.id)}
              className={
                "truncate rounded-md px-3 py-2 text-left text-sm " +
                (activeId === c.id ? "bg-brand text-white" : "hover:bg-slate-100")
              }
            >
              {c.title}
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="px-1 text-xs text-slate-400">No conversations yet.</p>
          )}
        </div>
      </aside>

      {/* Chat panel */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          {remaining !== null && (
            <span className="text-xs text-slate-500">
              {remaining.toLocaleString()} tokens remaining
            </span>
          )}
          {activeId && (
            <Button onClick={exportCase} disabled={exporting} variant="ghost">
              {exporting ? "Generating…" : "Export case PDF"}
            </Button>
          )}
        </div>
        {exportMsg && <p className="text-sm text-green-600">{exportMsg}</p>}

        <Card className="flex min-h-[45vh] flex-col gap-3">
          {messages.length === 0 && (
            <p className="text-slate-500">
              Tell me what happened. For example: “I was fired yesterday.”
            </p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={
                m.role === "user"
                  ? "max-w-[80%] self-end whitespace-pre-wrap rounded-lg bg-brand px-3 py-2 text-sm text-white"
                  : "max-w-[80%] self-start whitespace-pre-wrap rounded-lg bg-slate-100 px-3 py-2 text-sm"
              }
            >
              {m.content}
            </div>
          ))}
          {busy && <Spinner label="Francessca is typing…" />}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </Card>

        {docs.length > 0 && (
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="text-slate-500">Attach documents:</span>
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
                  className={
                    "rounded-full border px-2 py-0.5 " +
                    (on
                      ? "border-brand bg-brand/10 text-brand"
                      : "border-slate-300 text-slate-500")
                  }
                >
                  {d.filename}
                </button>
              );
            })}
          </div>
        )}

        <form onSubmit={send} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message…"
          />
          <Button type="submit" disabled={busy}>
            Send
          </Button>
        </form>
        <Disclaimer />
      </section>
    </main>
  );
}
