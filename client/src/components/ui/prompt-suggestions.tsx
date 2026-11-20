import { MapPin, Plane, Hotel } from 'lucide-react';

interface PromptSuggestionsProps {
  label: string;
  append: (message: { role: "user"; content: string }) => void;
  suggestions: string[];
}

export function PromptSuggestions({
  label,
  append,
  suggestions,
}: PromptSuggestionsProps) {
  // Get icon for each suggestion type
  const getIcon = (suggestion: string) => {
    if (suggestion.toLowerCase().includes('hotel')) {
      return <Hotel size={20} />;
    } else if (suggestion.toLowerCase().includes('flight')) {
      return <Plane size={20} />;
    } else {
      return <MapPin size={20} />;
    }
  };

  return (
    <div className="flex flex-col items-center justify-center w-full max-w-2xl mx-auto px-4 py-8">
      <h2 className="text-xl font-bold mb-6">{label}</h2>
      
      <div className="w-full space-y-4 md:space-y-0 md:grid md:grid-cols-1 md:gap-4">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => append({ role: "user", content: suggestion })}
            className="w-full flex items-center border border-border rounded-xl p-4 hover:bg-accent transition-colors text-left"
          >
            <div className="mr-3 text-muted-foreground">
              {getIcon(suggestion)}
            </div>
            <span className="text-foreground">{suggestion}</span>
          </button>
        ))}
      </div>
    </div>
  );
}