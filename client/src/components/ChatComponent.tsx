import { ChangeEvent, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ArrowDown, Pencil, RotateCcw } from 'lucide-react';
import { useAuth0 } from '@auth0/auth0-react';

import { MessageRow } from '@/components/ui/message-row';
import { Notice } from '@/components/ui/notice';
import { Button } from '@/components/ui/button';
import { CopyButton } from '@/components/ui/copy-button';
import { AnswerMarkdown } from '@/components/chat/answer-markdown';
import { ResultCards } from '@/components/chat/result-cards';
import { WeatherNote } from '@/components/chat/weather-note';
import { AgentProgress } from '@/components/chat/agent-progress';
import { Composer, type ComposerHandle } from '@/components/chat/composer';
import { ChatWelcome } from '@/components/chat/chat-welcome';
import type { ChatMessage } from '@/components/chat/types';

type ChatComponentProps = {
  messages: ChatMessage[];
  input: string;
  pending: boolean;
  pendingSince: number | null;
  ready: boolean;
  onInputChange: (e: ChangeEvent<HTMLTextAreaElement>) => void;
  onSend: () => void;
  onPick: (prompt: string) => void;
  onRetry: (errorId: string) => void;
  onEdit: (errorId: string) => void;
  onNewTrip: () => void;
};

const NEAR_BOTTOM_PX = 120;

const ERROR_COPY: Record<NonNullable<ChatMessage['error']>['kind'], { title: string; body: string }> = {
  timeout: {
    title: 'No answer after 2 minutes',
    body: 'The planners took too long. Try again, or ask for a smaller part of the trip first (for example, just hotels).',
  },
  network: {
    title: "Couldn't reach TravelBuddy",
    body: 'Check your connection, then try again. Your question is still here.',
  },
  server: {
    title: 'Something went wrong on our side',
    body: 'The planner hit an error before it could answer. Trying again usually works.',
  },
  incomplete: {
    title: 'The answer stopped before it finished',
    body: 'The server closed the connection mid-answer. Try again; nothing was lost.',
  },
};

function ErrorTurn({ message, onRetry, onEdit, onNewTrip, disabled }: { message: ChatMessage; onRetry: () => void; onEdit: () => void; onNewTrip: () => void; disabled: boolean }) {
  const copy = ERROR_COPY[message.error?.kind ?? 'server'];
  return (
    <Notice
      tone="error"
      className="max-w-prose"
      title={copy.title}
      description={<p>{copy.body}{message.error?.message && message.error.kind === 'server' ? <span className="mt-1 block text-meta text-muted-foreground">Details: {message.error.message}</span> : null}</p>}
      actions={
        <>
          <Button size="sm" onClick={onRetry} disabled={disabled}><RotateCcw aria-hidden="true" />Try again</Button>
          <Button size="sm" variant="outline" onClick={onEdit} disabled={disabled}><Pencil aria-hidden="true" />Edit question</Button>
          <Button size="sm" variant="ghost" onClick={onNewTrip}>Start a new trip</Button>
        </>
      }
    />
  );
}

export default function ChatComponent({
  messages, input, pending, pendingSince, ready,
  onInputChange, onSend, onPick, onRetry, onEdit, onNewTrip,
}: ChatComponentProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<ComposerHandle>(null);
  const nearBottom = useRef(true);
  const [showJump, setShowJump] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const { user } = useAuth0();
  const userInitial = (user?.given_name || user?.name || user?.email || '?').trim().charAt(0).toUpperCase();
  const isEmpty = messages.length === 0;

  const scrollToBottom = useCallback((smooth = true) => {
    const el = scrollRef.current;
    if (!el) return;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth && !reduce ? 'smooth' : 'auto' });
  }, []);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    nearBottom.current = distance < NEAR_BOTTOM_PX;
    if (nearBottom.current) setShowJump(false);
  };

  // First paint of a saved conversation: start at the latest turn.
  useLayoutEffect(() => {
    if (ready && !isEmpty) scrollToBottom(false);
    // Only on first ready; later turns are handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, scrollToBottom]);

  // New turns: follow only if the reader is already at the bottom, or it's
  // their own message. Otherwise offer "Jump to latest".
  const lastId = messages[messages.length - 1]?.id;
  const lastRole = messages[messages.length - 1]?.role;
  useEffect(() => {
    if (!lastId) return;
    if (lastRole === 'user' || nearBottom.current) {
      requestAnimationFrame(() => scrollToBottom());
    } else {
      setShowJump(true);
    }
  }, [lastId, lastRole, scrollToBottom]);

  useEffect(() => {
    if (pending && nearBottom.current) requestAnimationFrame(() => scrollToBottom());
  }, [pending, scrollToBottom]);

  // Screen-reader announcements for the slow, async parts.
  const prevPending = useRef(pending);
  useEffect(() => {
    if (pending && !prevPending.current) setAnnouncement('Planning your trip. This usually takes 20 to 40 seconds.');
    if (!pending && prevPending.current) {
      const last = messages[messages.length - 1];
      setAnnouncement(last?.status === 'error' ? 'Something went wrong. Options to try again are below.' : 'Your answer is ready.');
    }
    prevPending.current = pending;
  }, [pending, messages]);

  const handleEdit = (id: string) => {
    onEdit(id);
    requestAnimationFrame(() => composerRef.current?.focus());
  };

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <p className="sr-only" role="status" aria-live="polite">{announcement}</p>

      <div ref={scrollRef} onScroll={onScroll} className="scroll-thin min-h-0 flex-1 overflow-y-auto overscroll-contain">
        {!ready ? (
          <div className="mx-auto w-full max-w-3xl space-y-4 px-4 py-6" aria-hidden="true">
            <div className="ml-auto h-12 w-2/3 animate-breathe rounded-2xl bg-muted" />
            <div className="h-32 w-full animate-breathe rounded-xl bg-muted" />
          </div>
        ) : isEmpty && !pending ? (
          <ChatWelcome onPick={onPick} />
        ) : (
          <div className="mx-auto w-full max-w-3xl px-4 py-6">
            <h2 className="sr-only">Conversation</h2>
            <ol className="space-y-8">
              {messages.map((m) => (
                <li key={m.id} className="animate-rise-in">
                  {m.role === 'user' ? (
                    <MessageRow role="user" initial={userInitial}>
                      <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{m.content}</p>
                    </MessageRow>
                  ) : m.status === 'error' ? (
                    <MessageRow role="assistant">
                      <ErrorTurn
                        message={m}
                        disabled={pending}
                        onRetry={() => onRetry(m.id)}
                        onEdit={() => handleEdit(m.id)}
                        onNewTrip={onNewTrip}
                      />
                    </MessageRow>
                  ) : (
                    <MessageRow
                      role="assistant"
                      footer={<CopyButton content={m.content} copyMessage="Answer copied" label="Copy answer" />}
                    >
                      <AnswerMarkdown>{m.content}</AnswerMarkdown>
                      <WeatherNote data={m.data} answer={m.content} />
                      <ResultCards data={m.data} />
                    </MessageRow>
                  )}
                </li>
              ))}
              {pending && pendingSince && (
                <li>
                  <MessageRow role="assistant">
                    <AgentProgress since={pendingSince} />
                  </MessageRow>
                </li>
              )}
            </ol>
          </div>
        )}
      </div>

      {showJump && (
        <button
          type="button"
          onClick={() => { scrollToBottom(); setShowJump(false); }}
          className="absolute bottom-28 left-1/2 z-10 inline-flex h-10 -translate-x-1/2 animate-rise-in items-center gap-1.5 rounded-full border bg-background px-4 text-sm font-medium text-ink shadow-overlay hover:bg-muted pointer-coarse:h-11"
        >
          <ArrowDown className="size-4" aria-hidden="true" />
          Jump to latest
        </button>
      )}

      <div className="shrink-0 border-t bg-background px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <Composer
          ref={composerRef}
          value={input}
          onChange={onInputChange}
          onSend={onSend}
          pending={pending}
          disabled={!ready}
        />
      </div>
    </div>
  );
}
