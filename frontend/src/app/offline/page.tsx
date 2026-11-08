"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import {
  deleteModel,
  generateReply,
  isModelDownloaded,
  isModelLoaded,
  loadModel,
  OFFLINE_MODELS,
  stopGenerating,
  webGpuAvailable,
  type ChatTurn,
  type OfflineModelKey,
} from "@/lib/offlineModel";
import { InstallApp } from "@/components/InstallApp";
import { Markdown } from "@/components/Markdown";
import { Button, Card, Disclaimer, Textarea } from "@/components/ui";

const CHAT_KEY = "francessca_offline_chat";
const MODEL_KEY = "francessca_offline_model";

function readChat(): ChatTurn[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(CHAT_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** Ask the service worker to keep a copy of everything this page loaded,
 *  so it opens next time with no connection at all. */
function cachePageForOffline() {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.ready
    .then((registration) => {
      const urls = new Set<string>([window.location.pathname]);
      document
        .querySelectorAll<HTMLScriptElement>("script[src]")
        .forEach((el) => urls.add(el.src));
      document
        .querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"], link[rel="preload"]')
        .forEach((el) => urls.add(el.href));
      performance
        .getEntriesByType("resource")
        .filter((entry) => entry.name.includes("/_next/"))
        .forEach((entry) => urls.add(entry.name));
      registration.active?.postMessage({ type: "CACHE_URLS", urls: [...urls] });
    })
    .catch(() => {});
}

export default function OfflinePage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [supported, setSupported] = useState<boolean | null>(null);
  const [online, setOnline] = useState(true);
  const [model, setModel] = useState<OfflineModelKey>("small");
  const [downloaded, setDownloaded] = useState<Record<OfflineModelKey, boolean>>({
    small: false,
    standard: false,
  });
  const [ready, setReady] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [synced, setSynced] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSupported(webGpuAvailable());
    setMessages(readChat());
    setOnline(navigator.onLine);
    const stored = window.localStorage.getItem(MODEL_KEY);
    if (stored === "small" || stored === "standard") setModel(stored);
    setReady(isModelLoaded());
    void Promise.all([isModelDownloaded("small"), isModelDownloaded("standard")]).then(
      ([small, standard]) => {
        setDownloaded({ small, standard });
        // Prefer whichever the user already has.
        if (!stored && standard && !small) setModel("standard");
      },
    );
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    // Give the page a moment to finish loading its chunks first.
    const timer = window.setTimeout(cachePageForOffline, 3000);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem(CHAT_KEY, JSON.stringify(messages));
    setSynced(false);
  }, [messages]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [messages, streaming]);

  const start = useCallback(async () => {
    setError(null);
    setProgress(0);
    try {
      await loadModel(model, (fraction) => setProgress(fraction));
      window.localStorage.setItem(MODEL_KEY, model);
      setDownloaded((d) => ({ ...d, [model]: true }));
      setReady(true);
      cachePageForOffline(); // the model runtime chunk is loaded now too
    } catch (err) {
      setError(t("off.loadError", { detail: (err as Error).message }));
    } finally {
      setProgress(null);
    }
  }, [model, t]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || streaming !== null) return;
    const history: ChatTurn[] = [...messages, { role: "user", content: text }];
    setMessages(history);
    setDraft("");
    setStreaming("");
    setError(null);
    try {
      const reply = await generateReply(history, setStreaming);
      setMessages([...history, { role: "assistant", content: reply }]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStreaming(null);
    }
  }

  async function remove() {
    if (!window.confirm(t("off.deleteConfirm"))) return;
    await deleteModel(model).catch(() => {});
    setDownloaded((d) => ({ ...d, [model]: false }));
    setReady(false);
  }

  /** Hand the offline notes to the full assistant as one message. */
  async function continueOnline() {
    setSyncing(true);
    setError(null);
    try {
      const transcript = messages
        .map((m) => `${m.role === "user" ? t("off.me") : "Francessca"}: ${m.content}`)
        .join("\n\n");
      await api.sendMessage({ message: `${t("off.syncIntro")}\n\n${transcript}` });
      setSynced(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSyncing(false);
    }
  }

  const size = OFFLINE_MODELS[model].sizeMb;
  const sizeLabel = size >= 1000 ? `${(size / 1000).toFixed(1)} GB` : `${size} MB`;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 px-4 py-6 sm:px-6 sm:py-10">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t("off.title")}</h1>
          <span
            className={
              "rounded-full px-2 py-0.5 text-[11px] font-medium " +
              (online ? "bg-slate-100 text-slate-500" : "bg-amber-50 text-amber-700")
            }
          >
            {online ? t("off.online") : t("off.offline")}
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-500">{t("off.subtitle")}</p>
      </div>

      {supported === false && (
        <Card className="border-amber-200 bg-amber-50 text-sm text-amber-800">
          {t("off.unsupported")}
        </Card>
      )}

      {supported && !ready && (
        <Card>
          <h2 className="font-semibold text-slate-900">
            {downloaded[model] ? t("off.startTitle") : t("off.downloadTitle")}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {downloaded[model] ? t("off.startBody") : t("off.downloadBody", { size: sizeLabel })}
          </p>
          <div className="mt-4 grid grid-cols-2 gap-2">
            {(Object.keys(OFFLINE_MODELS) as OfflineModelKey[]).map((key) => (
              <button
                key={key}
                type="button"
                disabled={progress !== null}
                onClick={() => setModel(key)}
                className={
                  "rounded-xl border px-3 py-2.5 text-start text-sm transition-colors " +
                  (model === key
                    ? "border-brand bg-brand-50 text-brand-700"
                    : "border-slate-200 text-slate-600 hover:bg-slate-50")
                }
              >
                <span className="block font-medium">
                  {key === "small" ? t("off.modelSmall") : t("off.modelStandard")}
                </span>
                <span className="block text-xs opacity-80">
                  {key === "small" ? t("off.modelSmallHint") : t("off.modelStandardHint")}
                  {downloaded[key] ? ` · ✓ ${t("off.onDevice")}` : ""}
                </span>
              </button>
            ))}
          </div>
          {progress !== null ? (
            <div className="mt-4">
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-brand transition-all"
                  style={{ width: `${Math.round(progress * 100)}%` }}
                />
              </div>
              <p className="mt-1.5 text-xs text-slate-500">
                {t("off.preparing", { percent: Math.round(progress * 100) })}
              </p>
            </div>
          ) : (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button onClick={start} disabled={!downloaded[model] && !online}>
                {downloaded[model] ? t("off.start") : t("off.download", { size: sizeLabel })}
              </Button>
              {!downloaded[model] && !online && (
                <span className="text-xs text-amber-700">{t("off.needOnline")}</span>
              )}
            </div>
          )}
        </Card>
      )}

      {(messages.length > 0 || ready) && (
        <Card className="flex flex-col gap-3 p-4">
          {messages.length === 0 && (
            <p className="py-6 text-center text-sm text-slate-400">{t("chat.emptyPrompt")}</p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "flex justify-end" : "flex"}>
              <div
                className={
                  "max-w-[88%] rounded-2xl px-3.5 py-2 text-sm " +
                  (m.role === "user"
                    ? "rounded-br-sm bg-brand text-white"
                    : "rounded-bl-sm bg-slate-100 text-slate-800")
                }
              >
                {m.role === "user" ? (
                  <span className="whitespace-pre-wrap">{m.content}</span>
                ) : (
                  <Markdown text={m.content} />
                )}
              </div>
            </div>
          ))}
          {streaming !== null && (
            <div className="flex">
              <div className="max-w-[88%] rounded-2xl rounded-bl-sm bg-slate-100 px-3.5 py-2 text-sm text-slate-800">
                {streaming ? <Markdown text={streaming} /> : t("chat.typing")}
              </div>
            </div>
          )}
          <div ref={bottom} />

          {ready ? (
            <form
              onSubmit={send}
              className="flex items-end gap-2 rounded-xl border border-slate-200 p-1.5 focus-within:border-brand"
            >
              <Textarea
                bare
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    e.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder={t("chat.typeMessage")}
              />
              {streaming !== null ? (
                <Button type="button" variant="secondary" onClick={stopGenerating}>
                  {t("off.stop")}
                </Button>
              ) : (
                <Button type="submit" disabled={!draft.trim()}>
                  {t("chat.send")}
                </Button>
              )}
            </form>
          ) : (
            <p className="text-xs text-slate-400">{t("off.startToContinue")}</p>
          )}
        </Card>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {messages.length > 0 && streaming === null && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {user && user.role !== "lawyer" && online && !synced && (
            <Button variant="secondary" disabled={syncing} onClick={continueOnline}>
              {syncing ? t("lp.sending") : t("off.continueOnline")}
            </Button>
          )}
          {synced && (
            <Link href="/chat" className="font-medium text-brand underline">
              {t("off.syncedOpenChat")}
            </Link>
          )}
          <Button
            variant="ghost"
            onClick={() => window.confirm(t("off.clearConfirm")) && setMessages([])}
          >
            {t("off.clear")}
          </Button>
        </div>
      )}

      <Card className="p-4">
        <p className="mb-3 text-sm text-slate-600">{t("off.privacy")}</p>
        <InstallApp showOfflineLink={false} />
        {downloaded[model] && (
          <button className="mt-3 text-xs text-slate-400 underline" onClick={remove}>
            {t("off.deleteModel")}
          </button>
        )}
      </Card>
      <Disclaimer />
    </main>
  );
}
