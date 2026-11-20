import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { CalendarPlus, Map as MapIcon, Plus } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

import { LocationProvider, useLocation as useMapLocations, type Location } from '@/components/LocationContext';
import { TravelMapComponent } from '@/components/TravelMapComponent';
import ChatComponent from '@/components/ChatComponent';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';
import { displayLocale } from '@/lib/format';
import { destinationOf, type ChatMessage } from '@/components/chat/types';
import { TripActions, downloadItineraryIcs } from '@/components/chat/itinerary';
import { Button } from '@/components/ui/button';

/** Calendar / PDF / Share for the latest day-by-day plan, always in reach. */
function HeaderTripActions({ messages, conversationId }: { messages: ChatMessage[]; conversationId: string }) {
  const latest = [...messages].reverse().find((m) => m.role === 'assistant' && !m.status && m.data?.itinerary?.days?.length);
  if (!latest?.data) return null;
  return (
    <span className="flex shrink-0 items-center gap-1" role="group" aria-label="Trip actions">
      <Button size="sm" variant="ghost" onClick={() => downloadItineraryIcs(latest.data!)} aria-label="Add to calendar" title="Add the plan to your calendar (.ics)">
        <CalendarPlus aria-hidden="true" />
      </Button>
      <TripActions compact tripId={latest.serverId ? conversationId : undefined} />
    </span>
  );
}

/** "20–25 Dec", "28 Dec – 2 Jan" from ISO dates. */
function dateRange(start?: string, end?: string) {
  const d = (x?: string) => (x ? new Date(`${x}T12:00:00`) : null);
  const a = d(start), b = d(end);
  if (!a || Number.isNaN(a.getTime())) return null;
  const fmt = (x: Date, o: Intl.DateTimeFormatOptions) => x.toLocaleDateString(displayLocale(), o);
  if (!b || Number.isNaN(b.getTime()) || start === end) return fmt(a, { day: 'numeric', month: 'short' });
  if (a.getMonth() === b.getMonth() && a.getFullYear() === b.getFullYear()) return `${a.getDate()}–${fmt(b, { day: 'numeric', month: 'short' })}`;
  return `${fmt(a, { day: 'numeric', month: 'short' })} – ${fmt(b, { day: 'numeric', month: 'short' })}`;
}

/** Destination · dates · travelers from the latest answer, as one segmented pill. */
function TripBar({ messages }: { messages: ChatMessage[] }) {
  const latest = [...messages].reverse().find((m) => m.role === 'assistant' && (m.data?.trip || m.data?.itinerary));
  if (!latest?.data) return null;
  const it = latest.data.itinerary?.trip;
  const trip = latest.data.trip;
  const place = (destinationOf(latest.data)?.name ?? it?.destination?.name)?.split(',')[0]?.trim();
  const dates = dateRange(trip?.start_date ?? it?.start_date, trip?.end_date ?? it?.end_date);
  const adults = trip?.adults ?? it?.travelers?.adults;
  const kids = trip?.children ?? it?.travelers?.children ?? 0;
  const people = adults ? adults + kids : null;
  const parts = [place, dates, people ? `${people} traveler${people > 1 ? 's' : ''}` : null].filter(Boolean) as string[];
  if (!parts.length) return null;
  return (
    <p className="hidden min-w-0 items-center overflow-hidden rounded-full border bg-card text-sm text-ink shadow-xs sm:inline-flex" aria-label={`Trip: ${parts.join(', ')}`}>
      {parts.map((t, i) => (
        <span key={i} className={cn('truncate px-3 py-1 tabular', i > 0 && 'border-l', i === 0 && 'font-semibold')}>{t}</span>
      ))}
    </p>
  );
}

/** Router state other pages can pass to start a trip (see HomePage). */
type LaunchState = { prompt?: string } | null;

function ChatArea({ id, mapToggle, openMap }: { id: string; mapToggle: React.ReactNode; openMap: () => void }) {
  const navigate = useNavigate();
  const routerLocation = useLocation();
  const chat = useChat(id);
  const { clearDetectedLocations, addDetectedLocations, setSelectedLocation } = useMapLocations();

  // "Day 2 on map": show just that day's stops.
  const showOnMap = useCallback((pins: Location[]) => {
    clearDetectedLocations();
    setSelectedLocation(null);
    addDetectedLocations(pins);
    openMap();
  }, [clearDetectedLocations, addDetectedLocations, setSelectedLocation, openMap]);

  const startNewTrip = useCallback(() => {
    navigate(`/chat/${uuidv4()}`, { viewTransition: true });
  }, [navigate]);

  // Auto-send a prompt handed over from /home once, then clear it so a
  // refresh doesn't send it again.
  const launched = useRef<string | null>(null);
  useEffect(() => {
    const prompt = (routerLocation.state as LaunchState)?.prompt;
    if (!prompt || !chat.isReady || launched.current === id) return;
    launched.current = id;
    navigate(routerLocation.pathname, { replace: true, state: null });
    if (chat.messages.length === 0) chat.send(prompt);
  }, [routerLocation.state, routerLocation.pathname, chat.isReady, chat.messages.length, chat, id, navigate]);

  const hasMessages = chat.messages.length > 0;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-12 shrink-0 items-center justify-between gap-2 border-b px-3">
        {hasMessages ? (
          <button
            type="button"
            onClick={startNewTrip}
            className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground pointer-coarse:h-11"
          >
            <Plus className="size-4" aria-hidden="true" />
            New trip
          </button>
        ) : (
          <span className="px-2 text-sm text-muted-foreground">New trip</span>
        )}
        <TripBar messages={chat.messages} />
        <span className="ml-auto flex items-center gap-1">
          <HeaderTripActions messages={chat.messages} conversationId={id} />
        </span>
        {mapToggle && (
          <span className="flex items-center gap-1">
            {mapToggle}
          </span>
        )}
      </div>

      <ChatComponent
        messages={chat.messages}
        input={chat.input}
        pending={chat.status === 'pending'}
        pendingSince={chat.pendingSince}
        ready={chat.isReady}
        onInputChange={chat.handleInputChange}
        onSend={() => chat.send(chat.input)}
        onPick={(prompt) => chat.send(prompt)}
        onRetry={chat.retry}
        onEdit={chat.editFailed}
        onNewTrip={startNewTrip}
        onStop={chat.stop}
        onShowOnMap={showOnMap}
        onAnswerClarification={chat.answerClarification}
        onFeedback={chat.giveFeedback}
        conversationId={id}
      />
    </div>
  );
}

export default function ChatMainPage() {
  const { id = '' } = useParams();
  // Below xl (1280px) the map is opt-in so the conversation and composer keep the
  // full height. At xl and up, chat and map sit side by side.
  const [mapOpen, setMapOpen] = useState(false);
  const openMap = useCallback(() => setMapOpen(true), []);

  const mapToggle = (
    <button
      type="button"
      onClick={() => setMapOpen((v) => !v)}
      aria-expanded={mapOpen}
      aria-controls="trip-map"
      className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground xl:hidden pointer-coarse:h-11"
    >
      <MapIcon className="size-4" aria-hidden="true" />
      <span className="sr-only sm:not-sr-only">{mapOpen ? 'Hide map' : 'Show map'}</span>
    </button>
  );

  return (
    <LocationProvider>
      <h1 className="sr-only">Trip planner chat</h1>
      <div className="flex min-h-0 flex-1 flex-col xl:flex-row">
        <section aria-label="Conversation" className="flex min-h-0 flex-1 flex-col xl:w-[55%] xl:flex-none xl:border-r">
          {/* key: a fresh chat state per conversation id */}
          <ChatArea key={id} id={id} mapToggle={mapToggle} openMap={openMap} />
        </section>
        <section
          id="trip-map"
          aria-label="Trip map"
          className={cn(
            'min-h-0 border-t xl:block xl:flex-1 xl:border-t-0',
            mapOpen ? 'block h-[45dvh] shrink-0 xl:h-auto' : 'hidden'
          )}
        >
          <TravelMapComponent />
        </section>
      </div>
    </LocationProvider>
  );
}
