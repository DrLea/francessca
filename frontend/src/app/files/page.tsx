"use client";

import { useEffect, useRef, useState } from "react";
import { api, type DocumentMeta } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { Badge, Button, Card, Spinner } from "@/components/ui";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.tiff,.docx,.txt";
const MAX_MB = 25;

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function FilesPage() {
  const { user, loading } = useRequireAuth();
  const [files, setFiles] = useState<DocumentMeta[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user) return;
    api.listFiles().then(setFiles).catch((e) => setError(e.message));
  }, [user]);

  async function onSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File exceeds ${MAX_MB} MB.`);
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
        {loading && <Spinner label="Loading…" />}
      </div>
    );

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-1 text-2xl font-semibold">Documents</h1>
      <p className="mb-6 text-sm text-slate-500">
        Upload PDF, image, DOCX, or TXT files (max {MAX_MB} MB). Text is extracted
        automatically — including OCR for images — so Francessca can use it.
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
          {uploading ? "Uploading…" : "Upload a document"}
        </Button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </Card>

      <div className="mt-6 flex flex-col gap-2">
        {files.map((d) => (
          <Card key={d.id} className="flex items-center justify-between py-3">
            <div>
              <div className="font-medium">{d.filename}</div>
              <div className="text-xs text-slate-500">
                {humanSize(d.size)} · {new Date(d.uploaded_at).toLocaleDateString()}
              </div>
            </div>
            {d.has_extracted_text ? (
              <Badge>Text extracted</Badge>
            ) : (
              <span className="text-xs text-slate-400">No text</span>
            )}
          </Card>
        ))}
        {files.length === 0 && (
          <p className="text-sm text-slate-400">No documents uploaded yet.</p>
        )}
      </div>
    </main>
  );
}
