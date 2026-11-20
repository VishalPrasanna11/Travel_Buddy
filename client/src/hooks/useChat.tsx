import { useState, useEffect, useCallback, useRef, ChangeEvent } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAuth0 } from '@auth0/auth0-react';

import { askTravelQuestion, AskError, type TravelResponse } from '@/api/LLMApi';
import { chatDb, type Conversation } from '@/db/indexedDb';
import { useLocation as useMapLocations, type Location } from '@/components/LocationContext';
import { attractionsOf, type ChatMessage, type ResponseData } from '@/components/chat/types';

const NEW_TITLE = 'New trip';
const DATA_KEYS = ['status', 'location', 'restaurants', 'attractions', 'attractions_list', 'hotels', 'flights', 'weather'] as const;

/** Keep only the structured fields we render; never the raw blob. */
function pickData(response: TravelResponse): ResponseData | undefined {
  const data: Record<string, unknown> = {};
  for (const key of DATA_KEYS) {
    if (response[key] !== undefined && response[key] !== null) data[key] = response[key];
  }
  return Object.keys(data).length ? (data as ResponseData) : undefined;
}

/** Map pins from returned coordinates only. */
export function locationsFromData(data?: ResponseData): Location[] {
  if (!data) return [];
  const out: Location[] = [];
  for (const a of attractionsOf(data)) {
    if (a.location?.lat != null && a.location?.lng != null) {
      out.push({ name: a.name, lat: a.location.lat, lng: a.location.lng, type: 'primary', formattedAddress: a.address });
    }
  }
  for (const h of data.hotels?.data ?? []) {
    if (h.geoCode?.latitude != null && h.geoCode?.longitude != null) {
      out.push({ name: h.name, lat: h.geoCode.latitude, lng: h.geoCode.longitude, type: 'secondary', relevanceScore: 90 });
    }
  }
  for (const r of data.restaurants ?? []) {
    if (r.location?.lat != null && r.location?.lng != null) {
      out.push({ name: r.name, lat: r.location.lat, lng: r.location.lng, type: 'reference', formattedAddress: r.address });
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
    .filter((m) => m.status !== 'error' && m.content)
    .slice(-10)
    .map((m) => ({ role: m.role, content: m.content }));
}

export type ChatStatus = 'loading' | 'idle' | 'pending';

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<ChatStatus>('loading');
  const [pendingSince, setPendingSince] = useState<number | null>(null);

  const { user } = useAuth0();
  const { addDetectedLocations, clearDetectedLocations } = useMapLocations();

  // Refs guard against double submits and stale async results.
  const inFlight = useRef(false);
  const loadedId = useRef<string | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]);
  const abortRef = useRef<AbortController | null>(null);
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

    (async () => {
      try {
        await chatDb.init();
        const saved = await chatDb.getConversation(conversationId);
        if (cancelled) return;
        if (saved) {
          conversationRef.current = { title: saved.title, created_at: saved.created_at, customTitle: saved.customTitle };
          setMessages(saved.messages ?? []);
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
  }, [conversationId, addDetectedLocations, clearDetectedLocations]);

  // Persist after every change, but only once this conversation has loaded.
  useEffect(() => {
    if (loadedId.current !== conversationId || messages.length === 0) return;
    const meta = conversationRef.current;
    const firstUser = messages.find((m) => m.role === 'user');
    const title = meta.customTitle ? meta.title : meta.title === NEW_TITLE && firstUser ? titleFrom(firstUser.content) : meta.title;
    conversationRef.current = { ...meta, title };
    chatDb
      .saveConversation({ id: conversationId, title, created_at: meta.created_at, updated_at: Date.now(), messages, customTitle: meta.customTitle })
      .catch((err) => console.error('Could not save conversation', err));
  }, [messages, conversationId]);

  const ask = useCallback(
    async (userMessage: ChatMessage, prior: ChatMessage[]) => {
      const forId = conversationId;
      const controller = new AbortController();
      abortRef.current = controller;
      inFlight.current = true;
      setStatus('pending');
      setPendingSince(Date.now());

      try {
        const response = await askTravelQuestion(
          { query: userMessage.content, chat_history: historyFor(prior), chat_id: forId, user_email: user?.email },
          { signal: controller.signal }
        );
        if (controller.signal.aborted || loadedId.current !== forId) return;
        const data = pickData(response);
        const reply: ChatMessage = { id: uuidv4(), role: 'assistant', content: response.answer ?? '', createdAt: new Date(), data };
        setMessages((prev) => [...prev, reply]);
        const pins = locationsFromData(data);
        if (pins.length) addDetectedLocations(pins);
      } catch (err) {
        if (controller.signal.aborted || loadedId.current !== forId) return;
        const e = err instanceof AskError ? err : new AskError('network', 'Something went wrong while asking.');
        console.error('Ask failed', err);
        setMessages((prev) => [
          ...prev,
          { id: uuidv4(), role: 'assistant', content: '', status: 'error', error: { kind: e.kind, message: e.message }, replyTo: userMessage.id, createdAt: new Date() },
        ]);
      } finally {
        if (abortRef.current === controller) {
          inFlight.current = false;
          abortRef.current = null;
          setStatus('idle');
          setPendingSince(null);
        }
      }
    },
    [conversationId, user?.email, addDetectedLocations]
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
      const without = msgs.filter((m) => m.id !== errorId);
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
    setMessages(msgs.filter((m) => m.id !== errorId && m.id !== userMessage.id));
    setInput(userMessage.content);
  }, []);

  return {
    messages,
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
