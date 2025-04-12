import React, { useState, useEffect } from 'react';
import { useChat } from '@ai-sdk/react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

// Import your custom UI components
import { ChatContainer } from '@/components/ui/chat';
import { ChatForm } from '@/components/ui/chat';
import { MessageList } from '@/components/ui/message-list';
import { MessageInput } from '@/components/ui/message-input';
import { Button } from '@/components/ui/button';
import { type Message } from '@/components/ui/chat-message';

export function ChatPage() {
  const {
    messages: aiMessages,
    input,
    handleInputChange,
    handleSubmit,
    append,
    isLoading,
    stop,
  } = useChat();
  
  // Convert messages from UIMessage[] to Message[]
  const messages = aiMessages.map(msg => {
    return {
      id: msg.id,
      role: msg.role,
      content: msg.content?.toString() || "",
      createdAt: new Date()
    } as Message;
  });
  
  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const isEmpty = messages.length === 0;
  const isTyping = lastMessage?.role === "user";
  
  // For mobile prompt carousel
  const [currentIndex, setCurrentIndex] = useState(0);
  const suggestions = [
    "Plan a vacation to Paris?", 
    "Search a hotel in New York", 
    "Find flights to Tokyo"
  ];
  
  const isMobile = useMediaQuery('(max-width: 768px)');
  
  const handleSuggestionClick = (suggestion: string) => {
    append({
      role: "user",
      content: suggestion,
    });
  };
  
  const nextSuggestion = () => {
    setCurrentIndex((prev) => (prev + 1) % suggestions.length);
  };

  const prevSuggestion = () => {
    setCurrentIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
  };

  // Auto-rotate suggestions every 5 seconds on mobile
  useEffect(() => {
    if (!isMobile || !isEmpty) return;
    
    const interval = setInterval(() => {
      nextSuggestion();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [isMobile, isEmpty, currentIndex]);
  
  return (
    <ChatContainer className="flex flex-col h-[calc(95vh-64px)]"> {/* Adjust 64px to match your header height */}
      <div className="flex-1">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full">
            <h2 className="text-xl font-medium mb-6">Try asking</h2>
            
            {isMobile ? (
              /* Mobile: Show only one suggestion at a time with padding */
              <div className="w-full px-8">
                <div className="relative w-full">
                  <div className="flex items-center">
                    <button 
                      onClick={prevSuggestion}
                      className="p-2 rounded-full hover:bg-gray-100"
                    >
                      <ChevronLeft size={20} />
                    </button>
                    
                    <div className="flex-1 mx-2">
                      <Button
                        variant="outline"
                        className="w-full p-4 h-auto text-base justify-start"
                        onClick={() => handleSuggestionClick(suggestions[currentIndex])}
                      >
                        {suggestions[currentIndex]}
                      </Button>
                    </div>
                    
                    <button 
                      onClick={nextSuggestion}
                      className="p-2 rounded-full hover:bg-gray-100"
                    >
                      <ChevronRight size={20} />
                    </button>
                  </div>
                  
                  {/* Pagination dots */}
                  <div className="flex justify-center mt-4 space-x-2">
                    {suggestions.map((_, index) => (
                      <div 
                        key={index}
                        className={`h-2 w-2 rounded-full cursor-pointer ${
                          index === currentIndex ? 'bg-gray-800' : 'bg-gray-300'
                        }`}
                        onClick={() => setCurrentIndex(index)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              /* Desktop: Show all suggestions */
              <div className="flex flex-wrap justify-center gap-4 px-4">
                {suggestions.map((suggestion) => (
                  <Button
                    key={suggestion}
                    variant="outline"
                    className="p-6 h-auto text-base justify-start"
                    onClick={() => handleSuggestionClick(suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="chat-messages">
            <MessageList messages={messages} isTyping={isTyping} />
          </div>
        )}
      </div>
      
      <ChatForm
        className="sticky bottom-0 bg-background"
        isPending={isLoading || isTyping}
        handleSubmit={handleSubmit}
      >
        {({ files, setFiles }) => (
          <MessageInput
            value={input}
            onChange={handleInputChange}
            allowAttachments
            files={files}
            setFiles={setFiles}
            stop={stop}
            isGenerating={isLoading}
          />
        )}
      </ChatForm>
    </ChatContainer>
  );
}

// Media query hook
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => setMatches(event.matches);
    mediaQuery.addEventListener("change", handler);
    
    return () => mediaQuery.removeEventListener("change", handler);
  }, [query]);

  return matches;
}