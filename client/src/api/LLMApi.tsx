import type { AgentKey, AgentState, ChatErrorKind, SectionKey } from "@/components/chat/types";

const API_BASE_URL = import.meta.env.VITE_BASE_URL;

/** Longest we wait for one answer before telling the user it timed out. */
export const ASK_TIMEOUT_MS = 120_000;

type Message = { role: string; content: string };

export type TravelQuestion = {
  query: string;
  chat_history?: Message[];
  chat_id?: string;
  user_email?: string;
};

/** Raw response: text answer plus whatever structured fields the agents returned. */
export type TravelResponse = {
  status: string;
  answer: string;
  model: string;
  chat_id?: string;
  [key: string]: unknown;
};

export class AskError extends Error {
  kind: ChatErrorKind;
  code?: string;
  requestId?: string;
  retryAfter?: number;
  constructor(kind: ChatErrorKind, message: string, extra: { code?: string; requestId?: string; retryAfter?: number } = {}) {
    super(message);
    this.kind = kind;
    Object.assign(this, extra);
  }
}

/**
 * POST /api/llm/ask-question. The server streams keep-alive spaces and then
 * one JSON document. Contract unchanged; this only adds a timeout and
 * typed errors so the UI can explain what happened.
 */
export async function askTravelQuestion(
  question: TravelQuestion,
  { signal, token }: { signal?: AbortSignal; token?: string } = {}
): Promise<TravelResponse> {
  const requestData = {
    query: question.query,
    chat_history: (question.chat_history || []).map((msg) => ({
      role: msg.role === "user" || msg.role === "assistant" || msg.role === "system" ? msg.role : "user",
      content: msg.content || "",
    })),
    chat_id: question.chat_id || "",
  };

  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), ASK_TIMEOUT_MS);
  const onAbort = () => timeout.abort();
  signal?.addEventListener("abort", onAbort);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/llm/ask-question`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(requestData),
      signal: timeout.signal,
    });
  } catch (err) {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
    if (timeout.signal.aborted && !signal?.aborted) {
      throw new AskError("timeout", "No answer after 2 minutes.");
    }
    if (signal?.aborted) throw err;
    throw new AskError("network", "Couldn't reach TravelBuddy. Check your connection.");
  }

  try {
    if (!response.ok) {
      const body = await response.json().catch(() => ({} as { detail?: string }));
      throw new AskError("server", body.detail || `The server returned an error (${response.status}).`);
    }
    const text = await response.text();
    try {
      return JSON.parse(text) as TravelResponse;
    } catch {
      // 200 + keep-alive bytes, then the server failed before sending JSON.
      throw new AskError("incomplete", "The answer stopped before it finished.");
    }
  } catch (err) {
    if (err instanceof AskError) throw err;
    if (timeout.signal.aborted && !signal?.aborted) {
      throw new AskError("timeout", "No answer after 2 minutes.");
    }
    if (signal?.aborted) throw err;
    throw new AskError("network", "The connection dropped while waiting for the answer.");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

// ------------------------------------------------------------- streaming

export type StreamEvent =
  | { event: "meta"; data: { request_id: string; schema_version?: string } }
  | { event: "agent"; data: { agent: AgentKey; state: AgentState; count?: number; message?: string } }
  | { event: "plan"; data: { sections: string[]; trip?: Record<string, unknown> } }
  | { event: "trip"; data: Record<string, unknown> }
  | { event: "section"; data: { type: SectionKey; section: { status: string; count?: number; items?: unknown[]; message?: string; forecast?: unknown } } }
  | { event: "delta"; data: { text: string } }
  | { event: "clarification"; data: { thread_id: string; question: string; missing: string[]; fields: unknown[]; trip?: unknown } }
  | { event: "final"; data: TravelResponse & { request_id: string } }
  | { event: "error"; data: { code: string; message: string; retryable?: boolean; section?: string; request_id?: string; retry_after?: number } };

export type StreamQuestion = {
  query: string;
  chat_history?: Message[];
  conversation_id?: string;
  resume?: Record<string, unknown>;
};

/** Server-Sent Events over fetch (EventSource can't POST or send a bearer token). */
async function* readSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<StreamEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep: number;
      while ((sep = buffer.search(/\r?\n\r?\n/)) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep).replace(/^\r?\n\r?\n/, "");
        let event = "message";
        const data: string[] = [];
        for (const line of raw.split(/\r?\n/)) {
          if (line.startsWith(":")) continue; // heartbeat comment
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
        }
        if (!data.length) continue;
        try {
          yield { event, data: JSON.parse(data.join("\n")) } as StreamEvent;
        } catch {
          /* ignore a malformed frame rather than failing the whole answer */
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/** Not worth retrying on the old endpoint: the server answered, just not well. */
class StreamRejected extends Error {}

/**
 * POST /api/llm/ask and yield SSE events as they arrive. If the streaming
 * endpoint can't be reached (older server, proxy that strips SSE), falls
 * back to /ask-question and replays its single JSON answer as events.
 */
export async function* streamTravelQuestion(
  question: StreamQuestion,
  { signal, token }: { signal?: AbortSignal; token?: string } = {}
): AsyncGenerator<StreamEvent> {
  const headers: Record<string, string> = { "Content-Type": "application/json", Accept: "text/event-stream" };
  if (token) headers.Authorization = `Bearer ${token}`;
  let sawEvent = false;
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        query: question.query,
        chat_history: question.chat_history ?? [],
        conversation_id: question.conversation_id,
        resume: question.resume,
      }),
      signal,
    });
    if (response.status === 429) {
      const retryAfter = Number(response.headers.get("Retry-After") || 0) || undefined;
      const body = await response.json().catch(() => ({}));
      throw new AskError("rate_limited", body?.error?.message || "Too many questions at once.", { retryAfter, requestId: body?.error?.request_id });
    }
    if (response.status === 401) throw new AskError("server", "Your session expired. Sign in again.", { code: "UNAUTHORIZED" });
    if (!response.ok || !response.body || !(response.headers.get("content-type") || "").includes("text/event-stream")) {
      if (response.status >= 400 && response.status < 500 && response.status !== 404 && response.status !== 405) {
        const body = await response.json().catch(() => ({}));
        throw new StreamRejected(body?.error?.message || body?.detail || `Request failed (${response.status}).`);
      }
      throw new Error(`stream unavailable (${response.status})`);
    }
    for await (const ev of readSSE(response.body)) {
      sawEvent = true;
      yield ev;
    }
    return;
  } catch (err) {
    if (signal?.aborted) throw err;
    if (err instanceof AskError) throw err;
    if (err instanceof StreamRejected) throw new AskError("server", err.message);
    if (sawEvent) throw new AskError("incomplete", "The connection dropped mid-answer.");
    console.warn("Streaming ask unavailable, falling back", err);
  }

  // Fallback: old endpoint, one JSON document.
  const legacy = await askTravelQuestion(
    { query: question.query, chat_history: question.chat_history, chat_id: question.conversation_id },
    { signal, token }
  );
  if (legacy.answer) yield { event: "delta", data: { text: legacy.answer } };
  yield { event: "final", data: { ...legacy, request_id: "" } };
}
