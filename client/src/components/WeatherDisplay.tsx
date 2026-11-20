import React from 'react';
import { MapPin, Cloud, CloudRain, Sun, Wind } from 'lucide-react';

interface WeatherDisplayProps {
  content: string;
}

const WeatherDisplay: React.FC<WeatherDisplayProps> = ({ content }) => {
  // Check if this is a weather response
  const isWeatherResponse = content.includes("Here's the current weather") || 
                           content.includes("weather information") ||
                           (content.includes("weather") && content.includes("•"));
  
  if (!isWeatherResponse) {
    return null;
  }
  
  // Parse the weather content
  const lines = content.split('\n\n');
  const title = lines[0];
  const locationData = lines.slice(1);
  
  // Helper function to get appropriate weather icon
  const getWeatherIcon = (text: string) => {
    const lowerText = text.toLowerCase();
    if (lowerText.includes('rain') || lowerText.includes('shower')) {
      return <CloudRain className="h-6 w-6 text-teal-ink" />;
    }
    if (lowerText.includes('cloud')) {
      return <Cloud className="h-6 w-6 text-muted-foreground" />;
    }
    if (lowerText.includes('sun') || lowerText.includes('clear')) {
      return <Sun className="h-6 w-6 text-amber-ink" />;
    }
    if (lowerText.includes('wind')) {
      return <Wind className="h-6 w-6 text-teal-ink" />;
    }
    return <Cloud className="h-6 w-6 text-muted-foreground" />;
  };
  
  // Extract temperature if available
  const extractTemperature = (text: string) => {
    const tempMatch = text.match(/(\d+)°C/);
    return tempMatch ? parseInt(tempMatch[1], 10) : null;
  };
  
  // If no location data is found, return null
  if (locationData.length === 0) {
    return null;
  }
  
  return (
    <div className="weather-display rounded-lg overflow-hidden border border-border mb-4">
      <div className="bg-muted p-3 border-b border-border">
        <h3 className="text-lg font-medium text-foreground">{title}</h3>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
        {locationData.map((line, index) => {
          // Extract location and weather info
          const match = line.match(/^• ([^:]+): (.+)$/);
          if (!match) return <div key={index}>{line}</div>;
          
          const [_, location, report] = match;
          const hasError = report.includes("couldn't retrieve") || report.includes("error");
          const temp = extractTemperature(report);
          
          return (
            <div 
              key={index} 
              className={`p-3 rounded-lg ${
                hasError ? 'bg-danger-tint border border-red/30' : 
                'bg-background border border-border shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <MapPin className="h-5 w-5 mr-2 text-foreground" />
                  <h4 className="font-medium text-foreground">{location}</h4>
                </div>
                
                {!hasError && (
                  <div className="flex items-center">
                    {getWeatherIcon(report)}
                    {temp && (
                      <span className="ml-2 text-lg font-medium text-foreground">{temp}°C</span>
                    )}
                  </div>
                )}
              </div>
              
              <p className="mt-2 text-sm text-muted-foreground">{report}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default WeatherDisplay;
