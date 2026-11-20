import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Map as MapIcon, Plus } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

import { LocationProvider, useLocation as useMapLocations, type Location } from '@/components/LocationContext';
import { TravelMapComponent } from '@/components/TravelMapComponent';
import ChatComponent from '@/components/ChatComponent';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';

/** Router state other pages can pass to start a trip (see HomePage). */
type LaunchState = { prompt?: string } | null;

function ChatArea({ id, mapToggle, openMap }: { id: string; mapToggle: React.ReactNode; openMap: () => void }) {
  const navigate = useNavigate();
  const routerLocation = useLocation();
  const chat = useChat(id);
  const { detectedLocations, clearDetectedLocations, addDetectedLocations, setSelectedLocation } = useMapLocations();

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
            className="inline-flex h-9 items-center gap-1.5 rounded-md px-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground pointer-coarse:h-11"
          >
            <Plus className="size-4" aria-hidden="true" />
            New trip
          </button>
        ) : (
          <span className="px-2 text-sm text-muted-foreground">New trip</span>
        )}
        {mapToggle && (
          <span className="flex items-center gap-1">
            {detectedLocations.length > 0 && (
              <span className="text-meta text-muted-foreground xl:hidden tabular">{detectedLocations.length} on map</span>
            )}
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
      className="inline-flex h-9 items-center gap-1.5 rounded-md px-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground xl:hidden pointer-coarse:h-11"
    >
      <MapIcon className="size-4" aria-hidden="true" />
      {mapOpen ? 'Hide map' : 'Show map'}
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
