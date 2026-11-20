import type { ChatErrorKind } from "@/components/chat/types";

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
  constructor(kind: ChatErrorKind, message: string) {
    super(message);
    this.kind = kind;
  }
}

/**
 * POST /api/llm/ask-question. The server streams keep-alive spaces and then
 * one JSON document. Contract unchanged; this only adds a timeout and
 * typed errors so the UI can explain what happened.
 */
export async function askTravelQuestion(
  question: TravelQuestion,
  { signal }: { signal?: AbortSignal } = {}
): Promise<TravelResponse> {
  const requestData = {
    query: question.query,
    chat_history: (question.chat_history || []).map((msg) => ({
      role: msg.role === "user" || msg.role === "assistant" || msg.role === "system" ? msg.role : "user",
      content: msg.content || "",
    })),
    chat_id: question.chat_id || "",
    user_email: question.user_email || "",
  };

  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), ASK_TIMEOUT_MS);
  const onAbort = () => timeout.abort();
  signal?.addEventListener("abort", onAbort);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/llm/ask-question`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
