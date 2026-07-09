"use client";

import { useEffect, useRef, useState } from "react";
import { api, type DocumentMeta } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Badge, Button, Card, Spinner } from "@/components/ui";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.tiff,.docx,.txt";
const MAX_MB = 25;

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

type FileAction = "download" | "translate" | "delete";

export default function FilesPage() {
  const { user, loading } = useRequireAuth();
  const { t, locale, lang } = useI18n();
  const [files, setFiles] = useState<DocumentMeta[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<Record<number, FileAction | undefined>>({});
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user) return;
    api.listFiles().then(setFiles).catch((e) => setError(e.message));
  }, [user]);

  async function onDownload(doc: DocumentMeta) {
    setError(null);
    setPending((p) => ({ ...p, [doc.id]: "download" }));
    try {
      await api.downloadFile(doc.id, doc.filename);
    } catch (err) {
      setError((err as Error).message || t("files.actionError"));
    } finally {
      setPending((p) => ({ ...p, [doc.id]: undefined }));
    }
  }

  async function onDownloadTranslated(doc: DocumentMeta) {
    setError(null);
    setPending((p) => ({ ...p, [doc.id]: "translate" }));
    try {
      const stem = doc.filename.replace(/\.[^./]+$/, "");
      await api.downloadTranslatedFile(doc.id, lang, `${stem}_${lang}.pdf`);
    } catch (err) {
      setError((err as Error).message || t("files.actionError"));
    } finally {
      setPending((p) => ({ ...p, [doc.id]: undefined }));
    }
  }

  async function onDelete(doc: DocumentMeta) {
    if (!window.confirm(t("files.deleteConfirm"))) return;
    setError(null);
    setPending((p) => ({ ...p, [doc.id]: "delete" }));
    try {
      await api.deleteFile(doc.id);
      setFiles((f) => f.filter((d) => d.id !== doc.id));
    } catch (err) {
      setError((err as Error).message || t("files.actionError"));
      setPending((p) => ({ ...p, [doc.id]: undefined }));
    }
  }

  async function onSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(t("files.sizeExceeds", { maxMb: MAX_MB }));
      return;
    }
    setUploading(true);
    try {
      const doc = await api.uploadFile(file);
      setFiles((f) => [doc, ...f]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  if (loading || !user)
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        {loading && <Spinner label={t("common.loading")} />}
      </div>
    );

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-slate-900">{t("files.title")}</h1>
      <p className="mb-6 text-sm text-slate-500">
        {t("files.subtitle", { maxMb: MAX_MB })}
      </p>

      <Card>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          onChange={onSelect}
          className="hidden"
        />
        <Button onClick={() => inputRef.current?.click()} disabled={uploading}>
          {uploading ? t("files.uploading") : t("files.uploadButton")}
        </Button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </Card>

      <div className="mt-6 flex flex-col gap-2">
        {files.map((d) => {
          const action = pending[d.id];
          return (
            <Card key={d.id} className="py-3 transition-shadow hover:shadow-lg">
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="truncate font-medium text-slate-800">{d.filename}</div>
                  <div className="text-xs text-slate-500">
                    {humanSize(d.size)} · {new Date(d.uploaded_at).toLocaleDateString(locale)}
                  </div>
                </div>
                {d.has_extracted_text ? (
                  <Badge>{t("files.textExtracted")}</Badge>
                ) : (
                  <span className="shrink-0 text-xs text-slate-400">{t("files.noText")}</span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
                <Button
                  variant="ghost"
                  className="!px-3 !py-1.5 text-xs"
                  disabled={!!action}
                  onClick={() => onDownload(d)}
                >
                  {action === "download" ? t("common.loading") : t("files.download")}
                </Button>
                <Button
                  variant="ghost"
                  className="!px-3 !py-1.5 text-xs"
                  disabled={!!action || !d.has_extracted_text}
                  title={d.has_extracted_text ? undefined : t("files.noTextForTranslation")}
                  onClick={() => onDownloadTranslated(d)}
                >
                  {action === "translate" ? t("files.translating") : t("files.downloadTranslated")}
                </Button>
                <Button
                  variant="ghost"
                  className="!px-3 !py-1.5 text-xs text-red-600 hover:bg-red-50"
                  disabled={!!action}
                  onClick={() => onDelete(d)}
                >
                  {action === "delete" ? t("files.deleting") : t("files.delete")}
                </Button>
              </div>
            </Card>
          );
        })}
        {files.length === 0 && (
          <p className="text-sm text-slate-400">{t("files.noDocuments")}</p>
        )}
      </div>
    </main>
  );
}
