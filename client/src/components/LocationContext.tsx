//trial - g

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// Updated Location interface
export interface Location {
  name: string;
  lat: number | null; // Allow null for unresolved locations
  lng: number | null; // Allow null for unresolved locations
  formattedAddress?: string;
  type?: 'primary' | 'secondary' | 'reference';
  relevanceScore?: number;
  placeId?: string;
  description?: string;
  isMock?: boolean; // Flag for mock/fallback results
}

export type Viewport = { low: { lat: number; lng: number }; high: { lat: number; lng: number } };

// Define context type
interface LocationContextType {
  /** Destination bounds from the first `trip` event, before any pins exist. */
  viewport: Viewport | null;
  setViewport: (v: Viewport | null) => void;
  detectedLocations: Location[];
  selectedLocation: Location | null;
  savedLocations: Location[];
  addDetectedLocations: (locations: Location[]) => void;
  clearDetectedLocations: () => void;
  setSelectedLocation: (location: Location | null) => void;
  addSavedLocation: (location: Location) => void;
  removeSavedLocation: (locationName: string) => void;
}

// Create the context
const LocationContext = createContext<LocationContextType | undefined>(undefined);

// Provider component
export function LocationProvider({ children }: { children: ReactNode }) {
  const [detectedLocations, setDetectedLocations] = useState<Location[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);
  const [savedLocations, setSavedLocations] = useState<Location[]>([]);
  const [viewport, setViewport] = useState<Viewport | null>(null);

  // Add new detected locations
  const addDetectedLocations = useCallback((locations: Location[]) => {
    setDetectedLocations(prev => {
      const merged = [...prev];

      locations.forEach(newLoc => {
        const existingIndex = merged.findIndex(loc =>
          loc.name === newLoc.name ||
          (newLoc.lat != null &&
           newLoc.lng != null &&
           loc.lat != null &&
           loc.lng != null &&
           Math.abs(loc.lat - newLoc.lat) < 0.0001 &&
           Math.abs(loc.lng - newLoc.lng) < 0.0001)
        );

        if (existingIndex >= 0) {
          if ((newLoc.relevanceScore || 0) > (merged[existingIndex].relevanceScore || 0)) {
            merged[existingIndex] = {
              ...merged[existingIndex],
              relevanceScore: newLoc.relevanceScore,
              type: newLoc.type || merged[existingIndex].type
            };
          }
        } else {
          merged.push(newLoc);
        }
      });

      return merged;
    });
  }, []);

  // Clear all detected locations
  const clearDetectedLocations = useCallback(() => {
    setDetectedLocations([]);
  }, []);

  // Add a location to saved locations
  const addSavedLocation = useCallback((location: Location) => {
    setSavedLocations(prev => {
      if (prev.some(loc => loc.name === location.name)) return prev;
      return [...prev, location];
    });
  }, []);

  // Remove a location from saved locations
  const removeSavedLocation = useCallback((locationName: string) => {
    setSavedLocations(prev => prev.filter(loc => loc.name !== locationName));
  }, []);

  return (
    <LocationContext.Provider
      value={{
        viewport,
        setViewport,
        detectedLocations,
        selectedLocation,
        savedLocations,
        addDetectedLocations,
        clearDetectedLocations,
        setSelectedLocation,
        addSavedLocation,
        removeSavedLocation
      }}
    >
      {children}
    </LocationContext.Provider>
  );
}

// Custom hook to use the location context
export function useLocation() {
  const context = useContext(LocationContext);
  if (context === undefined) {
    throw new Error('useLocation must be used within a LocationProvider');
  }
  return context;
}










