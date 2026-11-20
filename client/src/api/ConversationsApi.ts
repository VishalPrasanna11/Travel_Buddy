import { useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";

import type { ChatMessage, ResponseData } from "@/components/chat/types";

const API_BASE_URL = import.meta.env.VITE_BASE_URL ?? "";

/**
 * Bearer token for API calls. Returns undefined when signed out, and never
 * waits more than 5s on a token refresh. In local development only, a
 * VITE_DEV_BEARER token can stand in for a signed-in user (stripped from
 * production builds).
 */
export function useApiToken() {
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();
  return useCallback(async (): Promise<string | undefined> => {
    if (!isAuthenticated) {
      return import.meta.env.DEV ? (import.meta.env.VITE_DEV_BEARER as string | undefined) || undefined : undefined;
    }
    const timeout = new Promise<undefined>((resolve) => setTimeout(() => resolve(undefined), 5000));
    return Promise.race([getAccessTokenSilently().catch(() => undefined), timeout]);
  }, [isAuthenticated, getAccessTokenSilently]);
}

export class ApiError extends Error {
  status: number;
  code?: string;
  requestId?: string;
  constructor(status: number, message: string, code?: string, requestId?: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

export async function api<T>(path: string, token: string | undefined, init: RequestInit = {}): Promise<T> {
  if (!token) throw new ApiError(401, "Sign in to sync.");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init.headers ?? {}) },
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(response.status, body?.error?.message || body?.detail || `Request failed (${response.status})`, body?.error?.code, body?.error?.request_id);
  }
  return body as T;
}

export type ServerConversation = {
  id: string;
  title: string;
  custom_title: boolean;
  created_at: string;
  updated_at: string;
  message_count?: number;
  messages?: { id: string; role: "user" | "assistant"; content: string; data?: ResponseData | null; request_id?: string; created_at?: string }[];
};

export const conversationsApi = {
  list: (token?: string, cursor?: string, limit = 30) =>
    api<{ items: ServerConversation[]; next_cursor: string | null }>(`/api/conversations?limit=${limit}${cursor ? `&cursor=${cursor}` : ""}`, token),
  get: (id: string, token?: string) => api<ServerConversation>(`/api/conversations/${encodeURIComponent(id)}`, token),
  rename: (id: string, title: string, token?: string) =>
    api<ServerConversation>(`/api/conversations/${encodeURIComponent(id)}`, token, { method: "PATCH", body: JSON.stringify({ title }) }),
  remove: (id: string, token?: string) => api<void>(`/api/conversations/${encodeURIComponent(id)}`, token, { method: "DELETE" }),
};

/** Server messages → chat turns (structured data included). */
export function toChatMessages(conv: ServerConversation): ChatMessage[] {
  return (conv.messages ?? []).map((m) => ({
    id: m.id,
    serverId: m.id,
    role: m.role,
    content: m.content,
    createdAt: m.created_at,
    data: m.data ?? undefined,
    requestId: m.request_id,
  }));
}

/** Stop an answer in flight on the server (best effort). */
export async function cancelAsk(requestId: string, token?: string) {
  try {
    await fetch(`${API_BASE_URL}/api/llm/ask/${encodeURIComponent(requestId)}`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    /* the client-side abort already stopped the stream */
  }
}

/** Ask the server for a checkout link for this flight/hotel/car. */
export function bookEntity(entityId: string, token?: string) {
  return api<{ url: string; checkout_mode?: string; kind: string }>(`/api/book/${encodeURIComponent(entityId)}`, token, { method: "POST" });
}

export function sendFeedback(body: { message_id: string; rating: "up" | "down"; reason?: string; request_id?: string }, token?: string) {
  return api<{ message_id: string; rating: string }>("/api/feedback", token, { method: "POST", body: JSON.stringify(body) });
}
