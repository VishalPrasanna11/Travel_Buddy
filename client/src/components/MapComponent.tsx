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
    address?: string;
    type?: 'primary' | 'secondary' | 'reference';
  }>;
  height?: string;
  width?: string;
  onMapClick?: (location: { lat: number; lng: number }) => void;
  /** Title of the marker to highlight (opens its info bubble) after focusing. */
  focusTitle?: string;
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

const WORLD = { lat: 20, lng: 0 };
// Keeps pins clear of the header and the "Places on the map" panel.
const FIT_PADDING = { top: 72, right: 56, bottom: 48, left: 48 };
const MAX_FIT_ZOOM = 16;

/**
 * Google map with brand pins. Framing has one owner: when the marker set
 * changes the map fits all pins (padding for overlays, capped zoom); when a
 * `center` is passed (a place picked from the list) it pans there at `zoom`.
 */
export default function MapComponent({
  center,
  zoom = 17,
  focusTitle,
  markers = [],
  height = "100%",
  width = "100%",
  onMapClick,
}: MapComponentProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [mapInstance, setMapInstance] = useState<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const infoRef = useRef<google.maps.InfoWindow | null>(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stableMarkers = useMemo(() => markers, [JSON.stringify(markers)]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stableCenter = useMemo(() => center, [center?.lat, center?.lng]);

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
          center: WORLD,
          zoom: 2,
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

    const iconConfig: Record<string, { fill: string; size: number }> = {
      primary: { fill: "#AA4465", size: 36 } /* attractions: raspberry */,
      secondary: { fill: "#F5A65B", size: 30 } /* hotels: amber */,
      reference: { fill: "#374151", size: 28 } /* restaurants: ink */,
    };

    infoRef.current ??= new google.maps.InfoWindow();
    const info = infoRef.current;

    const created = stableMarkers.map((markerData) => {
      const cfg = iconConfig[markerData.type || "primary"] || iconConfig.primary;
      const marker = new google.maps.Marker({
        position: { lat: markerData.lat, lng: markerData.lng },
        map: mapInstance,
        title: markerData.title || "Location",
        icon: {
          url: makePinSvg(cfg.fill, cfg.size),
          scaledSize: new google.maps.Size(cfg.size, cfg.size),
          anchor: new google.maps.Point(cfg.size / 2, cfg.size),
        },
      });

      marker.addListener("click", () => {
        // Build with DOM nodes, never HTML strings: names come from an API.
        const box = document.createElement("div");
        box.style.cssText = "padding:4px 2px;max-width:220px;font:14px/1.4 'Atkinson Hyperlegible Next',system-ui,sans-serif;color:#374151";
        const title = document.createElement("strong");
        title.textContent = markerData.title || "Location";
        box.appendChild(title);
        if (markerData.address) {
          const addr = document.createElement("div");
          addr.style.cssText = "font-size:13px;color:#5B6472;margin-top:2px";
          addr.textContent = markerData.address;
          box.appendChild(addr);
        }
        info.setContent(box);
        info.open({ map: mapInstance, anchor: marker });
      });
      return marker;
    });
    markersRef.current = created;

    if (created.length === 1) {
      mapInstance.setCenter({ lat: stableMarkers[0].lat, lng: stableMarkers[0].lng });
      mapInstance.setZoom(15);
    } else if (created.length > 1) {
      const bounds = new google.maps.LatLngBounds();
      stableMarkers.forEach((m) => bounds.extend({ lat: m.lat, lng: m.lng }));
      mapInstance.fitBounds(bounds, FIT_PADDING);
      google.maps.event.addListenerOnce(mapInstance, "idle", () => {
        if ((mapInstance.getZoom() ?? 0) > MAX_FIT_ZOOM) mapInstance.setZoom(MAX_FIT_ZOOM);
      });
    } else {
      mapInstance.setCenter(WORLD);
      mapInstance.setZoom(2);
    }

    // Remove exactly the markers this run created (safe under StrictMode).
    return () => {
      info.close();
      created.forEach((m) => {
        google.maps.event.clearInstanceListeners(m);
        m.setMap(null);
      });
    };
  }, [mapInstance, stableMarkers]);

  // A place picked from the list: pan to it close enough to separate
  // neighbouring pins.
  useEffect(() => {
    if (mapInstance && stableCenter) {
      mapInstance.panTo(stableCenter);
      mapInstance.setZoom(zoom);
      const target = focusTitle ? markersRef.current.find((m) => m.getTitle() === focusTitle) : undefined;
      if (target) google.maps.event.trigger(target, "click");
    }
  }, [mapInstance, stableCenter, zoom, focusTitle]);

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
