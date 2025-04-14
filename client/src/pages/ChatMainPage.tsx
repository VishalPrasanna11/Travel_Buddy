import { LocationProvider } from "@/components/LocationContext";
import { TravelMapComponent } from "@/components/TravelMapComponent";
import { useParams } from 'react-router-dom';
import { useChat } from "@/hooks/useChat";
import { PromptSuggestions } from "@/components/ui/prompt-suggestions";
import ChatComponent from "@/components/ChatComponent";
// import '@/styles/chat.css'; // Import the chat styles

export default function ChatMainPage() {
  const params = useParams();
  const { 
    messages, 
    input, 
    isTyping, 
    isLoading,
    handleInputChange,
    handleSubmit,
    append
  } = useChat(params.id);
  
  const isEmpty = messages.length === 0;

  // Travel suggestions
  const travelSuggestions = [
    "Plan a vacation to Paris?", 
    "Search a hotel in New York", 
    "Find flights to Tokyo"
  ];

  return (
    <LocationProvider>
      <div className="flex flex-col lg:flex-row h-[calc(100vh-64px)] overflow-hidden">
        <div className="w-full lg:w-1/2 h-1/2 lg:h-full border-r">
          <div className="h-full flex flex-col">
            <div className="p-2 border-b bg-white">
              <h2 className="text-xl font-semibold">TravelBuddy</h2>
            </div>
            
            <ChatComponent
              messages={messages}
              input={input}
              isTyping={isTyping}
              isLoading={isLoading}
              isEmpty={isEmpty}
              onInputChange={handleInputChange}
              onSubmit={handleSubmit}
            >
              {/* Use PromptSuggestions for empty state */}
              <PromptSuggestions 
                label="Travel Assistant"
                append={append}
                suggestions={travelSuggestions}
              />
            </ChatComponent>
          </div>
        </div>
        <div className="w-full lg:w-1/2 h-1/2 lg:h-full">
          <TravelMapComponent />
        </div>
      </div>
    </LocationProvider>
  );
}