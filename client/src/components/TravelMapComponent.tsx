import { useEffect, useState } from "react";
import MapComponent from "./MapComponent";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { MapPin, Map } from 'lucide-react';
import { useLocation, Location } from "./LocationContext";
import { Button } from "./ui/button";

export function TravelMapComponent() {
  const { 
    detectedLocations, 
    selectedLocation, 
    setSelectedLocation,
    clearDetectedLocations
  } = useLocation();
  
  const [markers, setMarkers] = useState<Array<{
    lat: number;
    lng: number;
    title?: string;
    type?: 'primary' | 'secondary' | 'reference';
  }>>([]);
  
  const [mapCenter, setMapCenter] = useState<{ lat: number; lng: number } | undefined>(undefined);
  const [mapZoom, setMapZoom] = useState(2); // Default to world view
  
  // Update markers when detected locations change
  useEffect(() => {
    if (!detectedLocations.length) {
      setMarkers([]);
      setMapCenter(undefined);
      setMapZoom(2);
      return;
    }
    
    // Filter valid locations (non-null lat/lng)
    const validLocations = detectedLocations.filter(
      loc => loc.lat != null && loc.lng != null
    ) as Location[]; // Assert non-null lat/lng for valid locations
    
    // Convert valid locations to markers
    const newMarkers = validLocations.map(location => ({
      lat: location.lat!, // Safe due to filter
      lng: location.lng!, // Safe due to filter
      title: location.name,
      type: location.type
    }));
    
    setMarkers(newMarkers);
    
    // Frame the pins: centre on their middle, zoom by how spread out they are
    // (a city's worth of places should open at street level, not continent).
    if (validLocations.length > 0) {
      const lats = validLocations.map(l => l.lat!);
      const lngs = validLocations.map(l => l.lng!);
      const span = Math.max(Math.max(...lats) - Math.min(...lats), Math.max(...lngs) - Math.min(...lngs));
      setMapCenter({ lat: (Math.max(...lats) + Math.min(...lats)) / 2, lng: (Math.max(...lngs) + Math.min(...lngs)) / 2 });
      setMapZoom(span < 0.02 ? 15 : span < 0.08 ? 13 : span < 0.3 ? 12 : span < 1 ? 10 : span < 5 ? 7 : span < 20 ? 5 : 3);
    } else {
      setMapCenter(undefined);
      setMapZoom(2);
    }
  }, [detectedLocations]);
  
  // Update center when selected location changes
  useEffect(() => {
    if (selectedLocation && selectedLocation.lat != null && selectedLocation.lng != null) {
      setMapCenter({ lat: selectedLocation.lat, lng: selectedLocation.lng });
      setMapZoom(10);
    }
  }, [selectedLocation]);
  
  // Handle map click to select location
  const handleMapClick = (location: { lat: number; lng: number }) => {
    const newLocation: Location = {
      name: `Selected Location (${location.lat.toFixed(4)}, ${location.lng.toFixed(4)})`,
      lat: location.lat,
      lng: location.lng,
      type: 'primary',
      relevanceScore: 100
    };
    
    setSelectedLocation(newLocation);
  };
  
  return (
    <Card className="relative h-full min-h-0 gap-0 rounded-none border-0 py-0 shadow-none">
      <CardHeader className="flex h-12 shrink-0 flex-row items-center justify-between border-b px-4 py-0">
        <CardTitle className="flex items-center text-sm font-semibold">
          <Map className="mr-2 h-4 w-4 text-raspberry" aria-hidden="true" />
          Travel Map
        </CardTitle>
        {detectedLocations.length > 0 && (
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => clearDetectedLocations()}
          >
            Clear Pins
          </Button>
        )}
      </CardHeader>
      <CardContent className="min-h-0 flex-1 p-0">
        <div className="h-full">
          <MapComponent 
            markers={markers}
            center={mapCenter}
            zoom={mapZoom}
            onMapClick={handleMapClick}
            height="100%"
          />
        </div>
      </CardContent>
      
      {/* Places on the map: collapsible list; each item recenters the map. */}
      {detectedLocations.length > 0 && (
        <details className="group/places absolute right-3 top-15 z-10 w-[min(18rem,calc(100%-1.5rem))] rounded-xl border bg-background shadow-overlay">
          <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 px-3 text-sm font-semibold [&::-webkit-details-marker]:hidden">
            <span className="flex items-center gap-1.5">
              <MapPin className="size-4 text-raspberry" aria-hidden="true" />
              Places on the map
              <span className="font-normal text-muted-foreground tabular">{detectedLocations.length}</span>
            </span>
            <span className="text-meta font-normal text-muted-foreground group-open/places:hidden">Show</span>
            <span className="hidden text-meta font-normal text-muted-foreground group-open/places:inline">Hide</span>
          </summary>
          <ul className="scroll-thin max-h-[min(320px,50dvh)] space-y-0.5 overflow-auto border-t p-1.5">
            {[...detectedLocations]
              .sort((a, b) => (b.relevanceScore || 0) - (a.relevanceScore || 0))
              .map((location, index) => {
                const selected = selectedLocation?.name === location.name;
                const dot = location.isMock
                  ? 'bg-red'
                  : location.type === 'primary' ? 'bg-raspberry' : location.type === 'secondary' ? 'bg-amber' : 'bg-ink';
                return (
                  <li key={`${location.name}-${index}`}>
                    <button
                      type="button"
                      onClick={() => setSelectedLocation(location)}
                      aria-pressed={selected}
                      className={`flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors duration-150 hover:bg-muted pointer-coarse:min-h-11 ${selected ? 'bg-raspberry-tint' : ''}`}
                    >
                      <span className={`mt-1.5 size-2 shrink-0 rounded-full ${dot}`} aria-hidden="true" />
                      <span className="min-w-0">
                        <span className="block font-medium leading-snug [overflow-wrap:anywhere]">{location.name}</span>
                        {location.isMock ? (
                          <span className="block text-meta text-destructive">Location not found</span>
                        ) : (
                          location.formattedAddress && <span className="block truncate text-meta text-muted-foreground">{location.formattedAddress}</span>
                        )}
                      </span>
                    </button>
                  </li>
                );
              })}
          </ul>
          <p className="flex gap-3 border-t px-3 py-2 text-meta text-muted-foreground">
            <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-raspberry" aria-hidden="true" />See</span>
            <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-amber" aria-hidden="true" />Stay</span>
            <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-ink" aria-hidden="true" />Eat</span>
          </p>
        </details>
      )}
    </Card>
  );
}





