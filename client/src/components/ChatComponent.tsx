import { ChangeEvent, ReactNode, useRef, useEffect } from 'react';
import { type Message } from '@/components/ui/chat-message';
import { ChatForm } from '@/components/ui/chat';
import { MessageInput } from '@/components/ui/message-input';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import WeatherDisplay from './WeatherDisplay';
import { MessageRow } from '@/components/ui/message-row';
import { useAuth0 } from '@auth0/auth0-react';
import type { Location } from './LocationContext';

// Define props including the location detection callback
type ChatComponentProps = {
  messages: Message[];
  input: string;
  isTyping: boolean;
  isLoading: boolean;
  isEmpty: boolean;
  onInputChange: (e: ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit: (event?: { preventDefault?: () => void }) => void;
  onLocationDetected?: (locations: Location[]) => void;
  children?: ReactNode;
};

export default function ChatComponent({
  messages,
  input,
  isTyping,
  isLoading,
  isEmpty,
  onInputChange,
  onSubmit,
  onLocationDetected,
  children
}: ChatComponentProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth0();
  const userInitial = (user?.given_name || user?.name || user?.email || '?').trim().charAt(0).toUpperCase();
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const processedMessagesRef = useRef<Set<string>>(new Set());

  // Scroll only the message list. scrollIntoView() also scrolls every
  // ancestor, which pushed the conversation under the sticky header.
  // (Phase 3 makes this conditional on the user already being at the bottom.)
  const scrollToBottom = () => {
    const el = chatContainerRef.current;
    if (!el) return;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    el.scrollTo({ top: el.scrollHeight, behavior: reduce ? 'auto' : 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Process messages for location data
  useEffect(() => {
    if (messages.length > 0 && onLocationDetected) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'assistant' && !processedMessagesRef.current.has(lastMessage.id)) {
        // Mark this message as processed to prevent reprocessing
        processedMessagesRef.current.add(lastMessage.id);
        processResponseForLocations(lastMessage.content);
      }
    }
  }, [messages, onLocationDetected]);

  // Extract location data from responses
  const processResponseForLocations = (content: string) => {
    if (!content || !onLocationDetected) return;
    
    try {
      // First try to find JSON data in the response
      const jsonMatches = content.match(/({[\s\S]*})/);
      
      if (jsonMatches && jsonMatches[0]) {
        try {
          const jsonStr = jsonMatches[0];
          const data = JSON.parse(jsonStr);
          const locations: Location[] = [];
          
          // Process attractions (from London format)
          if (data.attractions && Array.isArray(data.attractions)) {
            data.attractions.forEach((attraction: any) => {
              if (attraction.location?.lat && attraction.location?.lng) {
                locations.push({
                  name: attraction.name,
                  lat: attraction.location.lat,
                  lng: attraction.location.lng,
                  // address: attraction.address,
                  // rating: attraction.rating,
                  // photo_url: attraction.photo_url,
                  // total_ratings: attraction.total_ratings,
                  // types: attraction.types,
                  type: 'primary' // Set attractions as primary pins
                });
              }
            });
          }
          
          // Process attractions_list (from Boston format)
          if (data.attractions_list?.attractions && Array.isArray(data.attractions_list.attractions)) {
            data.attractions_list.attractions.forEach((attraction: any) => {
              if (attraction.location?.lat && attraction.location?.lng) {
                locations.push({
                  name: attraction.name,
                  lat: attraction.location.lat,
                  lng: attraction.location.lng,
                  // address: attraction.address,
                  // rating: attraction.rating,
                  // photo_url: attraction.photo_url,
                  // total_ratings: attraction.total_ratings,
                  // types: attraction.types,
                  type: 'primary'
                });
              }
            });
          }
          
          // Process hotels
          if (data.hotels?.data && Array.isArray(data.hotels.data)) {
            data.hotels.data.forEach((hotelOffer: any) => {
              if (hotelOffer.hotel?.location?.lat && hotelOffer.hotel?.location?.lng) {
                locations.push({
                  name: hotelOffer.hotel.name,
                  lat: hotelOffer.hotel.location.lat,
                  lng: hotelOffer.hotel.location.lng,
                  // address: hotelOffer.hotel.cityCode || "",
                  type: 'secondary', // Set hotels as secondary pins
                  relevanceScore: 90
                });
              }
            });
          }
          
          // Process restaurants
          if (data.restaurants && Array.isArray(data.restaurants)) {
            data.restaurants.forEach((restaurant: any) => {
              if (restaurant.location?.lat && restaurant.location?.lng) {
                locations.push({
                  name: restaurant.name,
                  lat: restaurant.location.lat,
                  lng: restaurant.location.lng,
                  // address: restaurant.address,
                  // rating: restaurant.rating,
                  // photo_url: restaurant.photo_url,
                  // total_ratings: restaurant.total_ratings,
                  // types: restaurant.types,
                  type: 'reference' // Set restaurants as reference pins
                });
              }
            });
          }
          
          if (locations.length > 0) {
            // console.log("Found locations in JSON:", locations);
            onLocationDetected(locations);
            return;
          }
        } catch (err) {
          console.error("Error parsing JSON:", err);
        }
      }
      
      // Fallback: try to extract coordinates from markdown text
      const locationRegex = /📍.*?(\-?\d+\.\d+),\s*(\-?\d+\.\d+)/g;
      const locations: Location[] = [];
      let match;
      
      while ((match = locationRegex.exec(content)) !== null) {
        const lat = parseFloat(match[1]);
        const lng = parseFloat(match[2]);
        
        if (!isNaN(lat) && !isNaN(lng)) {
          const nameMatch = content.match(/(\w+.*?)\s*📍/);
          const name = nameMatch ? nameMatch[1].trim() : "Location";
          
          locations.push({
            name,
            lat,
            lng,
            type: 'primary'
          });
        }
      }
      
      if (locations.length > 0) {
        // console.log("Found locations in text:", locations);
        onLocationDetected(locations);
      }
    } catch (err) {
      console.error("Error processing response for locations:", err);
    }
  };

  const stop = () => {
    // Since your API doesn't support streaming, this is a no-op
    // But we keep it for API compatibility
  };

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div 
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain chat-scrollbar"
        ref={chatContainerRef}
      >
        {isEmpty ? (
          <div className="flex min-h-full flex-col items-center justify-center">
            {children}
          </div>
        ) : (
          <div className="mx-auto w-full max-w-3xl px-4 py-6">
            <ol className="space-y-6" aria-label="Messages">
              {messages.map((message) => (
                <li key={message.id}>
                  {message.role === "user" ? (
                    <MessageRow role="user" initial={userInitial}>
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </MessageRow>
                  ) : (
                    <MessageRow
                      role="assistant"
                      footer={
                        // TODO(Phase 3): feedback isn't wired to anything yet.
                        <div className="flex items-center gap-1">
                          <button type="button" aria-label="Helpful" className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground pointer-coarse:size-11">
                            <ThumbsUp size={16} aria-hidden="true" />
                          </button>
                          <button type="button" aria-label="Not helpful" className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground pointer-coarse:size-11">
                            <ThumbsDown size={16} aria-hidden="true" />
                          </button>
                        </div>
                      }
                    >
                      <div className="max-w-prose text-base text-pretty">
                        <WeatherDisplay content={message.content} />
                        <div dangerouslySetInnerHTML={{ __html: convertMarkdownToHTML(message.content) }} />
                      </div>
                    </MessageRow>
                  )}
                </li>
              ))}
            </ol>

            {/* Interim waiting indicator; Phase 3 replaces it with agent progress. */}
            {isTyping && (
              <MessageRow role="assistant" className="mt-6">
                <div className="flex h-8 items-center" role="status">
                  <span className="typing-indicator" aria-hidden="true">
                    <span></span>
                    <span></span>
                    <span></span>
                  </span>
                  <span className="sr-only">TravelBuddy is working on your answer</span>
                </div>
              </MessageRow>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      
      <div className="shrink-0 border-t bg-background px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <ChatForm
          className="mx-auto w-full max-w-3xl"
          isPending={isLoading || isTyping}
          handleSubmit={onSubmit}
        >
          {() => (
            <MessageInput
              value={input}
              onChange={onInputChange}
              stop={stop}
              isGenerating={isLoading || isTyping}
              placeholder="Ask anything..."
            />
          )}
        </ChatForm>
      </div>
    </div>
  );
}

// Helper function to convert markdown to HTML
function convertMarkdownToHTML(markdown: string): string {
  // This is a very simple markdown converter
  // In a real app, you might want to use a library like marked.js
  
  // Convert links with location icon
  markdown = markdown.replace(
    /📍 ([^:]+):/g, 
    '<span class="flex items-center"><span class="mr-1"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 13C13.6569 13 15 11.6569 15 10C15 8.34315 13.6569 7 12 7C10.3431 7 9 8.34315 9 10C9 11.6569 10.3431 13 12 13Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 22C16 18 20 14.4183 20 10C20 5.58172 16.4183 2 12 2C7.58172 2 4 5.58172 4 10C4 14.4183 8 18 12 22Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></span><strong>$1:</strong></span>'
  );
  
  // Convert numbered lists
  markdown = markdown.replace(
    /^\d+\.\s+(.+)$/gm, 
    '<div class="flex items-start my-2"><span class="mr-2 min-w-[24px] font-bold">$&</span></div>'
  );
  
  // Convert bold text
  markdown = markdown.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  
  // Convert bullet points
  markdown = markdown.replace(
    /^\*\s+(.+)$/gm,
    '<div class="flex items-start my-2"><span class="mr-2">•</span><span>$1</span></div>'
  );
  
  // Convert paragraphs
  markdown = markdown.split('\n\n').map(para => `<p>${para}</p>`).join('');
  
  return markdown;
}