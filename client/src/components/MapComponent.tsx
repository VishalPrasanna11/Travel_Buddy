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
  /** Destination bounds: framed while there are no pins yet. */
  viewport?: { low: { lat: number; lng: number }; high: { lat: number; lng: number } } | null;
}

let optionsSet = false;

// Lucide glyphs (24×24, stroked) drawn inside the pin badge.
const GLYPHS: Record<string, string> = {
  primary: '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/>',
  secondary: '<path d="M2 20v-8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8"/><path d="M4 10V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4"/><path d="M12 4v6"/><path d="M2 18h20"/>',
  reference: '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/>',
};

/** Round category badge with a white ring, soft shadow and a short tail. */
function makePinSvg(type: string, fill: string, glyph: string, size: number) {
  const h = Math.round(size * 1.15);
  return `data:image/svg+xml,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${h}" viewBox="0 0 40 46">
      <defs><filter id="s" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="1.5" stdDeviation="1.6" flood-color="#1f2937" flood-opacity=".35"/></filter></defs>
      <g filter="url(#s)">
        <path d="M14.5 33.5 20 42l5.5-8.5z" fill="${fill}" stroke="white" stroke-width="2" stroke-linejoin="round"/>
        <circle cx="20" cy="19" r="16" fill="${fill}" stroke="white" stroke-width="3"/>
      </g>
      <g transform="translate(11 10) scale(.75)" fill="none" stroke="${type === "secondary" ? "#374151" : "white"}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">${glyph}</g>
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
  viewport,
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stableViewport = useMemo(() => viewport, [JSON.stringify(viewport)]);

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
      secondary: { fill: "#F5A65B", size: 34 } /* hotels: amber */,
      reference: { fill: "#374151", size: 32 } /* restaurants: ink */,
    };

    infoRef.current ??= new google.maps.InfoWindow();
    const info = infoRef.current;

    const created = stableMarkers.map((markerData) => {
      const kind = iconConfig[markerData.type || "primary"] ? markerData.type || "primary" : "primary";
      const cfg = iconConfig[kind];
      const h = Math.round(cfg.size * 1.15);
      const marker = new google.maps.Marker({
        position: { lat: markerData.lat, lng: markerData.lng },
        map: mapInstance,
        title: markerData.title || "Location",
        icon: {
          url: makePinSvg(kind, cfg.fill, GLYPHS[kind], cfg.size),
          scaledSize: new google.maps.Size(cfg.size, h),
          anchor: new google.maps.Point(cfg.size / 2, h * (42 / 46)),
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
    } else if (stableViewport) {
      // Results haven't arrived yet: open on the destination.
      mapInstance.fitBounds(
        new google.maps.LatLngBounds(stableViewport.low, stableViewport.high),
        FIT_PADDING
      );
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
  }, [mapInstance, stableMarkers, stableViewport]);

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
