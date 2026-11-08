// Typed API client for the Francessca backend.
// The JWT is persisted in localStorage and attached to every request.

// The desktop build serves the UI from the API process itself, so requests
// must be relative. It cannot signal that with an empty NEXT_PUBLIC_API_URL:
// in PowerShell `$env:X = ""` deletes the variable, and Next then inlines
// the localhost fallback below. Hence an explicit flag.
// "/api" rather than "": in the desktop build one process serves both the
// UI and the API, and pages like /chat and /lawyers exist on both sides.
const API_URL =
  process.env.NEXT_PUBLIC_SAME_ORIGIN_API === "1"
    ? "/api"
    : process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
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
  role: "user" | "lawyer" | "admin";
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
  bio?: string | null;
  years_experience?: number | null;
  consultation_fee?: string | null;
  office_hours?: string | null;
  rating_avg?: number | null;
  rating_count?: number;
  /** The lawyer has an account, so a case can be sent to them in-app. */
  accepts_requests?: boolean;
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

export interface DesktopDownload {
  platform: "windows" | "mac" | "linux";
  url: string;
  /** Optional: shown so visitors can verify an unsigned executable. */
  sha256: string | null;
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

// ---- Lawyer portal, orders, admin -----------------------------------------
export type OrderStatus =
  | "pending"
  | "accepted"
  | "declined"
  | "cancelled"
  | "closed_won"
  | "closed_lost";

export interface Review {
  id: number;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface CaseItem {
  id: number;
  title: string;
  case_type: string | null;
  created_at: string;
}

/** An order as the client who sent it sees it. */
export interface ClientOrder {
  id: number;
  status: OrderStatus;
  lawyer: {
    id: number;
    name: string;
    law_firm: string | null;
    city: string | null;
    email: string | null;
    phone: string | null;
  };
  case_title: string | null;
  message: string | null;
  quality_score: number;
  created_at: string;
  responded_at: string | null;
  closed_at: string | null;
  review: Review | null;
  can_review: boolean;
}

/** An order as the lawyer sees it. `client` is null until accepted. */
export interface LawyerOrder {
  id: number;
  status: OrderStatus;
  case_title: string | null;
  case_type: string | null;
  case_summary: Record<string, unknown>;
  message: string | null;
  quality_score: number;
  quality_breakdown: Record<string, number>;
  is_free: boolean;
  deal_value: number | null;
  created_at: string;
  responded_at: string | null;
  closed_at: string | null;
  client: { name: string | null; email: string; language: string } | null;
  review: Review | null;
}

export interface LawyerProfile {
  id: number;
  name: string;
  law_firm: string | null;
  city: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  photo_url: string | null;
  bio: string | null;
  years_experience: number | null;
  consultation_fee: string | null;
  office_hours: string | null;
  is_published: boolean;
  rating_avg: number | null;
  rating_count: number;
  languages: string[];
  specializations: string[];
}

export interface LawyerQuota {
  free_total: number;
  extra: number;
  used: number;
  remaining: number;
  free_remaining: number;
  contact_email: string | null;
}

export interface LawyerMe {
  approval: "pending" | "approved" | "rejected";
  profile: LawyerProfile;
  quota: LawyerQuota;
  profile_completeness: number;
}

export type LawyerProfileInput = Partial<
  Omit<LawyerProfile, "id" | "is_published" | "rating_avg" | "rating_count">
>;

export interface LawyerStats {
  orders: {
    received: number;
    pending: number;
    accepted: number;
    declined: number;
    in_progress: number;
    won: number;
    lost: number;
  };
  rates: {
    acceptance: number | null;
    win: number | null;
    avg_response_hours: number | null;
    avg_lead_quality: number | null;
  };
  rating: { average: number | null; count: number };
  finance: {
    revenue: number;
    deals: number;
    avg_deal: number | null;
    free_orders_used: number;
    paid_orders_used: number;
    platform_fees: number;
  };
  monthly: {
    month: string;
    received: number;
    accepted: number;
    won: number;
    revenue: number;
  }[];
}

export type FeedbackCategory = "lead_quality" | "platform" | "bug" | "idea" | "other";

export interface Feedback {
  id: number;
  lawyer_id: number;
  order_id: number | null;
  category: FeedbackCategory;
  rating: number | null;
  comment: string;
  status: "new" | "reviewed";
  admin_note: string | null;
  created_at: string;
}

export interface AdminFeedback extends Feedback {
  lawyer_name: string;
  lawyer_city: string | null;
  order_quality_score: number | null;
  order_case_title: string | null;
}

export interface LawyerApplication {
  id: number;
  name: string;
  email: string;
  law_firm: string | null;
  city: string | null;
  phone: string | null;
  website: string | null;
  message: string | null;
  status: "pending" | "approved" | "rejected";
  lawyer_id: number | null;
  user_id: number | null;
  created_at: string;
  reviewed_at: string | null;
  specializations: string[];
  languages: string[];
}

export interface LawyerAccount {
  id: number;
  name: string;
  email: string | null;
  city: string | null;
  law_firm: string | null;
  is_published: boolean;
  rating_avg: number | null;
  rating_count: number;
  orders_used: number;
  free_total: number;
  extra_orders: number;
  orders_remaining: number;
  created_at: string;
}

export interface AdminOverview {
  users: { clients: number; lawyers: number; admins: number };
  lawyers: { directory: number; registered: number; live: number; pending_approval: number };
  orders: Record<OrderStatus, number> & {
    total: number;
    accepted_total: number;
    avg_quality: number | null;
    reported_revenue: number;
  };
  feedback: { new: number; total: number };
  reviews: { total: number; average: number | null };
  activity: { conversations: number; cases: number; tokens: number };
  recent_orders: {
    id: number;
    status: OrderStatus;
    lawyer: string | null;
    client: string | null;
    case_title: string | null;
    quality_score: number;
    deal_value: number | null;
    created_at: string;
  }[];
  recent_users: {
    id: number;
    email: string;
    full_name: string | null;
    role: User["role"];
    created_at: string;
  }[];
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

  desktopDownloads: () =>
    request<{ version: string | null; items: DesktopDownload[] }>(
      "/public/downloads",
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
      // 504 carries the "the local model was too slow" explanation; show it
      // rather than a generic failure.
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

  // --- Client: send a case to a lawyer, follow it, review -----------------
  listCases: () => request<CaseItem[]>("/case"),

  sendCase: (body: {
    lawyer_id: number;
    case_id?: number;
    conversation_id?: number;
    message?: string;
  }) => request<ClientOrder>("/orders", { method: "POST", body: JSON.stringify(body) }),

  myOrders: () => request<ClientOrder[]>("/orders"),

  cancelOrder: (id: number) =>
    request<ClientOrder>(`/orders/${id}/cancel`, { method: "POST" }),

  reviewOrder: (id: number, body: { rating: number; comment?: string }) =>
    request<ClientOrder>(`/orders/${id}/review`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // --- Lawyer portal --------------------------------------------------------
  registerLawyer: (body: {
    email: string;
    password: string;
    name: string;
    city?: string;
    law_firm?: string;
    specializations?: string[];
    languages?: string[];
    language?: string;
  }) =>
    request<{ access_token: string }>("/auth/register-lawyer", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  lawyerMe: () => request<LawyerMe>("/lawyer/me"),

  updateLawyerProfile: (body: LawyerProfileInput) =>
    request<LawyerMe>("/lawyer/profile", { method: "PUT", body: JSON.stringify(body) }),

  lawyerOrders: () => request<LawyerOrder[]>("/lawyer/orders"),

  acceptOrder: (id: number) =>
    request<LawyerOrder>(`/lawyer/orders/${id}/accept`, { method: "POST" }),

  declineOrder: (id: number) =>
    request<LawyerOrder>(`/lawyer/orders/${id}/decline`, { method: "POST" }),

  closeOrder: (id: number, body: { outcome: "won" | "lost"; deal_value?: number }) =>
    request<LawyerOrder>(`/lawyer/orders/${id}/close`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  lawyerStats: () => request<LawyerStats>("/lawyer/stats"),

  lawyerFeedback: () => request<Feedback[]>("/lawyer/feedback"),

  sendFeedback: (body: {
    category: FeedbackCategory;
    comment: string;
    rating?: number;
    order_id?: number;
  }) => request<Feedback>("/lawyer/feedback", { method: "POST", body: JSON.stringify(body) }),

  // --- Admin ----------------------------------------------------------------
  adminOverview: () => request<AdminOverview>("/admin/overview"),

  adminApplications: (status?: LawyerApplication["status"]) =>
    request<LawyerApplication[]>(
      `/admin/lawyer-applications${status ? `?status_filter=${status}` : ""}`,
    ),

  adminDecideApplication: (id: number, decision: "approve" | "reject") =>
    request<LawyerApplication>(`/admin/lawyer-applications/${id}/${decision}`, {
      method: "POST",
    }),

  adminLawyerAccounts: () => request<LawyerAccount[]>("/admin/lawyer-accounts"),

  adminUpdateLawyerAccount: (
    id: number,
    body: { extra_orders?: number; is_published?: boolean },
  ) =>
    request<LawyerAccount>(`/admin/lawyer-accounts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  adminFeedback: (params: { status?: "new" | "reviewed"; category?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status_filter", params.status);
    if (params.category) qs.set("category", params.category);
    return request<{
      items: AdminFeedback[];
      summary: {
        new: number;
        total: number;
        by_category: Record<string, { count: number; avg_rating: number | null }>;
      };
    }>(`/admin/feedback?${qs.toString()}`);
  },

  adminUpdateFeedback: (
    id: number,
    body: { status?: "new" | "reviewed"; admin_note?: string },
  ) =>
    request<AdminFeedback>(`/admin/feedback/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  dashboard: () => request<DashboardData>("/dashboard"),
  usage: () => request<UsageData>("/usage"),
};
