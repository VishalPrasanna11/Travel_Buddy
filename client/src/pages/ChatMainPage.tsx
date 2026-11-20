import { LocationProvider, useLocation } from "@/components/LocationContext";
import { TravelMapComponent } from "@/components/TravelMapComponent";
import { useParams } from 'react-router-dom';
import { useChat } from "@/hooks/useChat";
import { PromptSuggestions } from "@/components/ui/prompt-suggestions";
import ChatComponent from "@/components/ChatComponent";
import { useEffect, useCallback, useState } from 'react';
import { Map as MapIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Location } from '@/components/LocationContext';

function ChatArea({ mapToggle }: { mapToggle?: React.ReactNode }) {
  const params = useParams();
  const { 
    messages, 
    input, 
    isTyping, 
    isLoading,
    handleInputChange,
    handleSubmit,
    append,
    resetChat
  } = useChat(params.id);
  
  const { addDetectedLocations, clearDetectedLocations } = useLocation();
  const isEmpty = messages.length === 0;

  // Clear locations when starting a new chat
  useEffect(() => {
    if (isEmpty) {
      clearDetectedLocations();
    }
  }, [isEmpty, clearDetectedLocations]);

  // Travel suggestions
  const travelSuggestions = [
    "Plan a vacation to Paris", 
    "Find hotels in New York", 
    "What are good attractions in Tokyo?"
  ];

  // Handler for detected locations - Using useCallback to prevent recreation on every render
  const handleLocationDetected = useCallback((locations: Location[]) => {
    if (locations && locations.length > 0) {
      // console.log("Adding locations to map from ChatComponent:", locations);
      addDetectedLocations(locations);
    }
  }, [addDetectedLocations]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-11 shrink-0 items-center justify-between gap-2 border-b px-4">
        {!isEmpty ? (
          <button
            onClick={resetChat}
            className="rounded-md text-sm text-muted-foreground hover:text-foreground"
          >
            Start New Chat
          </button>
        ) : <span />}
        {mapToggle}
      </div>

      <ChatComponent
        messages={messages}
        input={input}
        isTyping={isTyping}
        isLoading={isLoading}
        isEmpty={isEmpty}
        onInputChange={handleInputChange}
        onSubmit={handleSubmit}
        onLocationDetected={handleLocationDetected}
      >
        {/* Use PromptSuggestions for empty state */}
        <PromptSuggestions 
          label="Travel Assistant"
          append={append}
          suggestions={travelSuggestions}
        />
      </ChatComponent>
    </div>
  );
}

export default function ChatMainPage() {
  // Below lg the map is opt-in so the conversation and composer keep the
  // full height. At lg and up, chat and map sit side by side.
  const [mapOpen, setMapOpen] = useState(false);

  const mapToggle = (
    <button
      type="button"
      onClick={() => setMapOpen((v) => !v)}
      aria-expanded={mapOpen}
      aria-controls="trip-map"
      className="inline-flex h-9 items-center gap-1.5 rounded-md px-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground lg:hidden"
    >
      <MapIcon className="size-4" aria-hidden="true" />
      {mapOpen ? "Hide map" : "Show map"}
    </button>
  );

  return (
    <LocationProvider>
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <section aria-label="Conversation" className="flex min-h-0 flex-1 flex-col lg:w-1/2 lg:flex-none lg:border-r">
          <ChatArea mapToggle={mapToggle} />
        </section>
        <section
          id="trip-map"
          aria-label="Trip map"
          className={cn(
            "min-h-0 border-t lg:block lg:w-1/2 lg:border-t-0",
            mapOpen ? "block h-[45dvh] shrink-0 lg:h-auto" : "hidden"
          )}
        >
          <TravelMapComponent />
        </section>
      </div>
    </LocationProvider>
  );
}
