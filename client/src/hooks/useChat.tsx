import { useState, useEffect, useCallback, useRef, ChangeEvent } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { cancelAsk, conversationsApi, toChatMessages, useApiToken } from '@/api/ConversationsApi';

import { AskError, ASK_TIMEOUT_MS, streamTravelQuestion } from '@/api/LLMApi';
import { chatDb, type Conversation } from '@/db/indexedDb';
import { useLocation as useMapLocations, type Location } from '@/components/LocationContext';
import { attractionsOf, hotelsOf, restaurantsOf, type ChatMessage, type ResponseData } from '@/components/chat/types';
import { applyStreamEvent } from '@/hooks/stream-reducer';

const NEW_TITLE = 'New trip';

/** Map pins from returned coordinates only. */
export function locationsFromData(data?: ResponseData): Location[] {
  if (!data) return [];
  const out: Location[] = [];
  for (const a of attractionsOf(data)) {
    if (a.location?.lat != null && a.location?.lng != null) {
      out.push({ name: a.name, lat: a.location.lat, lng: a.location.lng, type: 'primary', formattedAddress: a.address, placeId: a.place_id });
    }
  }
  for (const h of hotelsOf(data)) {
    if (h.location?.lat != null && h.location?.lng != null) {
      out.push({ name: h.name, lat: h.location.lat, lng: h.location.lng, type: 'secondary', relevanceScore: 90, formattedAddress: h.address });
    }
  }
  for (const r of restaurantsOf(data)) {
    if (r.location?.lat != null && r.location?.lng != null) {
      out.push({ name: r.name, lat: r.location.lat, lng: r.location.lng, type: 'reference', formattedAddress: r.address, placeId: r.place_id });
    }
  }
  return out;
}

function titleFrom(text: string) {
  const clean = text.replace(/\s+/g, ' ').trim();
  return clean.length > 48 ? `${clean.slice(0, 47).trimEnd()}…` : clean || NEW_TITLE;
}

/** History sent to the model: real turns only, never our error placeholders. */
function historyFor(msgs: ChatMessage[]) {
  return msgs
    .filter((m) => !m.status && m.content)
    .slice(-10)
    .map((m) => ({ role: m.role, content: m.content }));
}

export type ChatStatus = 'loading' | 'idle' | 'pending';

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<ChatStatus>('loading');
  const [pendingSince, setPendingSince] = useState<number | null>(null);

  const getToken = useApiToken();
  const { addDetectedLocations, clearDetectedLocations, setViewport } = useMapLocations();

  // Refs guard against double submits and stale async results.
  const inFlight = useRef(false);
  const loadedId = useRef<string | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const tokenRef = useRef<string | undefined>(undefined);
  const conversationRef = useRef<Pick<Conversation, 'title' | 'created_at' | 'customTitle'>>({ title: NEW_TITLE, created_at: Date.now() });

  messagesRef.current = messages;

  // Load (or create) the conversation whenever the id changes.
  useEffect(() => {
    let cancelled = false;
    abortRef.current?.abort();
    inFlight.current = false;
    loadedId.current = null;
    setStatus('loading');
    setPendingSince(null);
    setMessages([]);
    setInput('');
    clearDetectedLocations();
    setViewport(null);

    (async () => {
      try {
        await chatDb.init();
        let saved = await chatDb.getConversation(conversationId);
        if (!saved) {
          // Not on this device: try the server copy (history syncs across devices).
          const token = await getToken();
          const remote = token ? await conversationsApi.get(conversationId, token).catch(() => null) : null;
          if (remote?.messages?.length) {
            saved = {
              id: remote.id,
              title: remote.title,
              customTitle: remote.custom_title,
              created_at: Date.parse(remote.created_at) || Date.now(),
              updated_at: Date.parse(remote.updated_at) || Date.now(),
              messages: toChatMessages(remote),
            };
          }
        }
        if (cancelled) return;
        if (saved) {
          conversationRef.current = { title: saved.title, created_at: saved.created_at, customTitle: saved.customTitle };
          // A turn saved mid-stream (tab closed) shows what arrived, not a spinner.
          setMessages((saved.messages ?? []).map((m) => (m.status === 'streaming' ? { ...m, status: undefined } : m)));
          const pins = (saved.messages ?? []).flatMap((m) => locationsFromData(m.data));
          if (pins.length) addDetectedLocations(pins);
        } else {
          conversationRef.current = { title: NEW_TITLE, created_at: Date.now() };
        }
      } catch (err) {
        console.error('Could not load conversation', err);
      } finally {
        if (!cancelled) {
          loadedId.current = conversationId;
          setStatus('idle');
        }
      }
    })();

    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, [conversationId, addDetectedLocations, clearDetectedLocations, setViewport, getToken]);

  // Persist after every change, but only once this conversation has loaded.
  useEffect(() => {
    if (loadedId.current !== conversationId || messages.length === 0) return;
    // Don't write IndexedDB on every token; save once the turn settles.
    if (messages.some((m) => m.status === 'streaming')) return;
    const meta = conversationRef.current;
    const firstUser = messages.find((m) => m.role === 'user');
    const title = meta.customTitle ? meta.title : meta.title === NEW_TITLE && firstUser ? titleFrom(firstUser.content) : meta.title;
    // (A server-generated title, when one arrives with `final`, has already replaced meta.title.)
    conversationRef.current = { ...meta, title };
    chatDb
      .saveConversation({ id: conversationId, title, created_at: meta.created_at, updated_at: Date.now(), messages, customTitle: meta.customTitle })
      .catch((err) => console.error('Could not save conversation', err));
  }, [messages, conversationId]);

  const ask = useCallback(
    async (userMessage: ChatMessage, prior: ChatMessage[], extra: { resume?: Record<string, unknown> } = {}) => {
      const forId = conversationId;
      const controller = new AbortController();
      abortRef.current = controller;
      inFlight.current = true;
      setStatus('pending');
      setPendingSince(Date.now());

      // One assistant turn that fills in as events arrive.
      const replyId = uuidv4();
      let reply: ChatMessage = { id: replyId, role: 'assistant', content: '', status: 'streaming', createdAt: new Date(), progress: {}, replyTo: userMessage.id };
      setMessages((prev) => [...prev, reply]);
      const update = (next: ChatMessage) => {
        reply = next;
        setMessages((prev) => prev.map((m) => (m.id === replyId ? next : m)));
      };
      const timer = setTimeout(() => controller.abort('timeout'), ASK_TIMEOUT_MS);
      let pinned = 0;

      try {
        const token = await getToken();
        tokenRef.current = token;
        const stream = streamTravelQuestion(
          { query: userMessage.content, chat_history: historyFor(prior), conversation_id: forId, ...extra },
          { signal: controller.signal, token }
        );
        for await (const ev of stream) {
          if (controller.signal.aborted || loadedId.current !== forId) return;
          if (ev.event === 'error') {
            // Section errors are partial results; the answer keeps streaming.
            if (ev.data.section) continue;
            throw new AskError(ev.data.code === 'CANCELLED' ? 'cancelled' : 'server', ev.data.message, { code: ev.data.code, requestId: ev.data.request_id });
          }
          const next = applyStreamEvent(reply, ev);
          update(next);
          if (ev.event === 'trip') {
            const vp = (ev.data as { destination?: { viewport?: Parameters<typeof setViewport>[0] } }).destination?.viewport;
            if (vp) setViewport(vp);
          }
          if (ev.event === 'final') {
            const title = (ev.data as { title?: string }).title;
            if (title && !conversationRef.current.customTitle) conversationRef.current = { ...conversationRef.current, title };
          }
          if (ev.event === 'section' || ev.event === 'final') {
            const pins = locationsFromData(next.data);
            if (pins.length > pinned) {
              addDetectedLocations(pins);
              pinned = pins.length;
            }
          }
        }
        if (reply.status === 'streaming') {
          // Stream closed without a final event.
          if (!reply.content) throw new AskError('incomplete', 'The answer stopped before it finished.');
          update({ ...reply, status: undefined });
        }
      } catch (err) {
        if (loadedId.current !== forId) return;
        const timedOut = controller.signal.reason === 'timeout';
        if (controller.signal.aborted && !timedOut && controller.signal.reason !== 'stop') return;
        const e = timedOut
          ? new AskError('timeout', 'No answer after 2 minutes.')
          : controller.signal.reason === 'stop'
            ? new AskError('cancelled', 'Stopped.')
            : err instanceof AskError ? err : new AskError('network', 'Something went wrong while asking.');
        if (e.kind !== 'cancelled') console.error('Ask failed', err);
        const keepPartial = reply.content || reply.data;
        setMessages((prev) => [
          ...prev.map((m) => (m.id === replyId && keepPartial ? { ...reply, status: undefined } : m)).filter((m) => m.id !== replyId || keepPartial),
          { id: uuidv4(), role: 'assistant', content: '', status: 'error', error: { kind: e.kind, message: e.message, code: e.code, requestId: e.requestId ?? reply.requestId, retryAfter: e.retryAfter }, replyTo: userMessage.id, createdAt: new Date() },
        ]);
      } finally {
        clearTimeout(timer);
        if (abortRef.current === controller) {
          inFlight.current = false;
          abortRef.current = null;
          setStatus('idle');
          setPendingSince(null);
        }
      }
    },
    [conversationId, getToken, addDetectedLocations, setViewport]
  );

  /** Send text as a new user turn. Ignored while an answer is pending. */
  const send = useCallback(
    (text: string) => {
      const content = text.trim();
      if (!content || inFlight.current || loadedId.current !== conversationId) return false;
      const prior = messagesRef.current;
      const userMessage: ChatMessage = { id: uuidv4(), role: 'user', content, createdAt: new Date() };
      setMessages((prev) => [...prev, userMessage]);
      setInput('');
      void ask(userMessage, prior);
      return true;
    },
    [ask, conversationId]
  );

  const handleSubmit = useCallback(
    (event?: { preventDefault?: () => void }) => {
      event?.preventDefault?.();
      send(input);
    },
    [input, send]
  );

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value);

  /** Retry a failed turn: drop the error and ask the same question again. */
  const retry = useCallback(
    (errorId: string) => {
      if (inFlight.current) return;
      const msgs = messagesRef.current;
      const errIdx = msgs.findIndex((m) => m.id === errorId);
      const err = msgs[errIdx];
      const userMessage = msgs.find((m) => m.id === err?.replyTo);
      if (!err || !userMessage) return;
      const without = msgs.filter((m) => m.id !== errorId && !(m.role === 'assistant' && m.replyTo === userMessage.id));
      const prior = without.slice(0, without.findIndex((m) => m.id === userMessage.id));
      setMessages(without);
      void ask(userMessage, prior);
    },
    [ask]
  );

  /** Put a failed question back in the composer so it can be changed. */
  const editFailed = useCallback((errorId: string) => {
    if (inFlight.current) return;
    const msgs = messagesRef.current;
    const err = msgs.find((m) => m.id === errorId);
    const userMessage = msgs.find((m) => m.id === err?.replyTo);
    if (!err || !userMessage) return;
    setMessages(msgs.filter((m) => m.id !== errorId && m.id !== userMessage.id && m.replyTo !== userMessage.id));
    setInput(userMessage.content);
  }, []);

  /** Stop the answer in flight (keeps whatever already arrived). */
  const stop = useCallback(() => {
    // Cancel server-side too (DELETE /api/llm/ask/{request_id}) so it stops spending tokens.
    const requestId = messagesRef.current.find((m) => m.status === 'streaming')?.requestId;
    if (requestId) void cancelAsk(requestId, tokenRef.current);
    abortRef.current?.abort('stop');
  }, []);

  return {
    messages,
    stop,
    input,
    setInput,
    status,
    pendingSince,
    isTyping: status === 'pending',
    isLoading: status === 'pending',
    isReady: status !== 'loading',
    handleInputChange,
    handleSubmit,
    send,
    retry,
    editFailed,
    /** Kept for compatibility with PromptSuggestions. */
    append: (m: { role: string; content: string }) => (m.role === 'user' ? send(m.content) : false),
  };
}
