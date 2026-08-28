// Typed API client for the Francessca backend.
// The JWT is persisted in localStorage and attached to every request.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "francessca_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string | null) {
  if (typeof window === "undefined") return;
  if (t) window.localStorage.setItem(TOKEN_KEY, t);
  else window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.body && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    const detail = await res
      .json()
      .catch(() => ({ detail: res.statusText }));
    throw new ApiError(detail.detail ?? `Request failed: ${res.status}`, res.status);
  }
  return res.json() as Promise<T>;
}

// ---- Types ----------------------------------------------------------------
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  language: string;
  role: "user" | "admin";
  tier: "free" | "premium";
  token_limit: number | null;
  tokens_used: number;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
}

/** A clarifying question the assistant attached to its reply. The UI always
 *  appends its own "Other" option with a free-text field, so `choices` never
 *  contains one (an empty `choices` means: ask as free text). */
export interface ClarifyQuestion {
  question: string;
  choices: string[];
}

/** One answer going back. `answer: null` means the user skipped it. */
export interface ClarifyAnswer {
  question: string;
  answer: string | null;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  token_count: number;
  created_at: string;
  questions?: ClarifyQuestion[];
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ChatResponse {
  conversation_id: number;
  /** The stored user turn — answers are composed into readable text server-side. */
  user_message: Message;
  message: Message;
  tokens_used: number;
  tokens_remaining: number | null;
}

export interface DocumentMeta {
  id: number;
  filename: string;
  size: number;
  mime: string;
  uploaded_at: string;
  has_extracted_text: boolean;
}

export interface Lawyer {
  id: number;
  name: string;
  law_firm: string | null;
  city: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  photo_url: string | null;
  specializations: string[];
  languages: string[];
}

export interface DashboardData {
  conversations: number;
  documents: number;
  cases: number;
  exports: number;
  timeline_events: number;
  tokens_used: number;
  token_limit: number | null;
}

export interface UsageData {
  token_limit: number | null;
  tokens_used: number;
  tokens_remaining: number | null;
  tier: string;
}

export interface CaseExportResult {
  case_id: number;
  pdf_export_id: number;
  zip_export_id?: number;
}

/** One calendar entry: an appointment, hearing, deadline or expiry date.
 *  Only entries pinned to a real day exist — `event_date` is never null. */
export interface TimelineEvent {
  id: number;
  event_date: string;
  date_label: string;
  description: string;
  is_deadline: boolean;
  source_type: "document" | "message" | "manual";
  /** Document id for `document` entries, message id for `message` entries. */
  source_id: number | null;
  /** Conversation to open, for entries extracted from chat. */
  conversation_id: number | null;
  /** Filename or conversation title; null once the source has been deleted. */
  source_label: string | null;
}

export interface Language {
  code: string;
  name: string;
}

/** Directory entry as shown to visitors who aren't signed in — no contact
 *  details; those stay behind the login on /lawyers. */
export interface LawyerPreview {
  id: number;
  name: string;
  law_firm: string | null;
  city: string | null;
  specializations: string[];
  languages: string[];
}

export interface LawyerApplicationInput {
  name: string;
  email: string;
  law_firm?: string;
  city?: string;
  phone?: string;
  website?: string;
  specializations?: string[];
  languages?: string[];
  message?: string;
}

// ---- API -----------------------------------------------------------------
export const api = {
  apiUrl: API_URL,

  register: (body: { email: string; password: string; full_name?: string }) =>
    request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  login: (body: { email: string; password: string }) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  google: (idToken: string) =>
    request<{ access_token: string }>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }),

  me: () => request<User>("/me"),

  updateMe: (body: { full_name?: string; language?: string }) =>
    request<User>("/me", { method: "PATCH", body: JSON.stringify(body) }),

  languages: () => request<Language[]>("/meta/languages"),

  // --- Public (no auth): the landing page ---------------------------------
  publicLawyers: (limit = 6) =>
    request<{ total: number; items: LawyerPreview[] }>(
      `/public/lawyers?limit=${limit}`,
    ),

  applyAsLawyer: (body: LawyerApplicationInput) =>
    request<{ id: number; status: string }>("/public/lawyer-applications", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Free while in beta: no payment step, this just moves the tier.
  changePlan: (tier: "free" | "premium") =>
    request<User>("/me/plan", { method: "POST", body: JSON.stringify({ tier }) }),

  timeline: () => request<TimelineEvent[]>("/case/timeline"),

  createTimelineEvent: (body: {
    event_date: string;
    description: string;
    is_deadline?: boolean;
  }) =>
    request<TimelineEvent>("/case/timeline", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteTimelineEvent: (id: number) =>
    request<void>(`/case/timeline/${id}`, { method: "DELETE" }),

  listConversations: () => request<Conversation[]>("/chat"),

  getConversation: (id: number) =>
    request<ConversationDetail>(`/chat/${id}`),

  // A whole batch of answers goes back in one request — one model call per
  // turn, exactly as with a typed message.
  sendMessage: (body: {
    conversation_id?: number;
    message?: string;
    answers?: ClarifyAnswer[];
    document_ids?: number[];
  }) => request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(body) }),

  listFiles: () => request<DocumentMeta[]>("/files"),

  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentMeta>("/files", { method: "POST", body: form });
  },

  deleteFile: (id: number) =>
    request<{ detail: string }>(`/files/${id}`, { method: "DELETE" }),

  // Fetches with the auth header attached and triggers a browser save —
  // same pattern as downloadExport, since plain <a href> can't send Bearer tokens.
  downloadFile: async (id: number, filename: string) => {
    const res = await fetch(`${API_URL}/files/${id}/download`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new ApiError("Download failed", res.status);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  },

  // Translates the document's extracted text into `lang` (typically the
  // currently selected UI language) and downloads the result as a PDF.
  downloadTranslatedFile: async (id: number, lang: string, filename: string) => {
    const res = await fetch(`${API_URL}/files/${id}/translate?lang=${encodeURIComponent(lang)}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(detail.detail ?? "Translation failed", res.status);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  },

  searchLawyers: (params: {
    specialization?: string;
    city?: string;
    language?: string;
  }) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v) as [string, string][],
    ).toString();
    return request<{ total: number; items: Lawyer[] }>(`/lawyers/search?${qs}`);
  },

  exportCase: (body: {
    conversation_id: number;
    title?: string;
    include_documents?: boolean;
  }) =>
    request<CaseExportResult>("/case/export", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Returns a URL the browser can open to download an export (token via fetch).
  downloadExport: async (exportId: number, filename: string) => {
    const res = await fetch(`${API_URL}/case/export/${exportId}/download`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new ApiError("Download failed", res.status);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  },

  dashboard: () => request<DashboardData>("/dashboard"),
  usage: () => request<UsageData>("/usage"),
};
