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

export interface Message {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  token_count: number;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ChatResponse {
  conversation_id: number;
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

  listConversations: () => request<Conversation[]>("/chat"),

  getConversation: (id: number) =>
    request<ConversationDetail>(`/chat/${id}`),

  sendMessage: (body: {
    conversation_id?: number;
    message: string;
    document_ids?: number[];
  }) => request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(body) }),

  listFiles: () => request<DocumentMeta[]>("/files"),

  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentMeta>("/files", { method: "POST", body: form });
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
