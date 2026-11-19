import { useEffect, useMemo, useRef, useState } from "react";
import { setOptions, importLibrary } from "@googlemaps/js-api-loader";
import { Skeleton } from "./ui/skeleton";

interface MapComponentProps {
  center?: { lat: number; lng: number };
  zoom?: number;
  markers?: Array<{
    lat: number;
    lng: number;
    title?: string;
    type?: 'primary' | 'secondary' | 'reference';
  }>;
  height?: string;
  width?: string;
  onMapClick?: (location: { lat: number; lng: number }) => void;
}

let optionsSet = false;

function makePinSvg(fill: string, size: number) {
  return `data:image/svg+xml,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">
      <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z" fill="${fill}" stroke="${fill}" stroke-width="2"/>
      <circle cx="12" cy="10" r="3" fill="white" stroke="white" stroke-width="2"/>
    </svg>
  `)}`;
}

export default function MapComponent({
  center = { lat: 40.7128, lng: -74.006 },
  zoom = 10,
  markers = [],
  height = "100%",
  width = "100%",
  onMapClick,
}: MapComponentProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [mapInstance, setMapInstance] = useState<google.maps.Map | null>(null);
  const [mapMarkers, setMapMarkers] = useState<google.maps.Marker[]>([]);
  const stableMarkers = useMemo(() => markers, [JSON.stringify(markers)]);
  const stableCenter = useMemo(() => center, [center.lat, center.lng]);

  useEffect(() => {
    const initializeMap = async () => {
      if (!mapRef.current) return;

      try {
        const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
        if (!apiKey) {
          console.error("Google Maps API key is missing");
          setLoading(false);
          return;
        }

        if (!optionsSet) {
          setOptions({ apiKey, version: "weekly" });
          optionsSet = true;
        }

        const { Map } = await importLibrary("maps") as google.maps.MapsLibrary;
        await importLibrary("places");

        const map = new Map(mapRef.current, {
          center,
          zoom,
          mapTypeControl: true,
          streetViewControl: true,
          fullscreenControl: true,
          zoomControl: true,
        });

        if (onMapClick) {
          map.addListener("click", (e: google.maps.MapMouseEvent) => {
            if (e.latLng) {
              onMapClick({
                lat: e.latLng.lat(),
                lng: e.latLng.lng(),
              });
            }
          });
        }

        setMapInstance(map);
        setLoading(false);
      } catch (error) {
        console.error("Error loading Google Maps:", error);
        setLoading(false);
      }
    };

    initializeMap();
  }, []);

  useEffect(() => {
    if (!mapInstance) return;

    mapMarkers.forEach((marker) => marker.setMap(null));

    const iconConfig: Record<string, { fill: string; size: number }> = {
      primary: { fill: "black", size: 36 },
      secondary: { fill: "#4B5563", size: 30 },
      reference: { fill: "#9CA3AF", size: 24 },
    };

    const newMarkers = stableMarkers.map((markerData) => {
      const cfg = iconConfig[markerData.type || "primary"] || iconConfig.primary;

      const marker = new google.maps.Marker({
        position: { lat: markerData.lat, lng: markerData.lng },
        map: mapInstance,
        title: markerData.title || "Location",
        animation: google.maps.Animation.DROP,
        icon: {
          url: makePinSvg(cfg.fill, cfg.size),
          scaledSize: new google.maps.Size(cfg.size, cfg.size),
          anchor: new google.maps.Point(cfg.size / 2, cfg.size),
        },
      });

      const infoWindow = new google.maps.InfoWindow({
        content: `
          <div style="padding: 8px; max-width: 200px;">
            <h3 style="font-weight: bold; margin-bottom: 4px;">${markerData.title || "Location"}</h3>
            <p style="font-size: 12px; margin: 0;">
              Lat: ${markerData.lat.toFixed(4)}, Lng: ${markerData.lng.toFixed(4)}
            </p>
          </div>
        `,
      });

      marker.addListener("click", () => {
        infoWindow.open(mapInstance, marker);
      });

      return marker;
    });

    setMapMarkers(newMarkers);

    if (newMarkers.length > 0) {
      const bounds = new google.maps.LatLngBounds();
      stableMarkers.forEach((m) => bounds.extend({ lat: m.lat, lng: m.lng }));
      mapInstance.fitBounds(bounds);

      google.maps.event.addListenerOnce(mapInstance, "bounds_changed", () => {
        const currentZoom = mapInstance?.getZoom() ?? 0;
        if (currentZoom > 15) mapInstance.setZoom(15);
      });
    }
  }, [mapInstance, stableMarkers]);

  useEffect(() => {
    if (mapInstance && stableCenter) {
      mapInstance.setCenter(stableCenter);
      mapInstance.setZoom(zoom);
    }
  }, [mapInstance, stableCenter, zoom]);

  return (
    <div className="relative w-full h-full">
      {loading && <Skeleton className="absolute inset-0 z-10" />}
      <div
        ref={mapRef}
        style={{ height, width }}
        className="rounded-md overflow-hidden"
      />
    </div>
  );
}
