import { useState } from "react";
import { BedDouble, Bookmark, Landmark, MapPin, Utensils } from "lucide-react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";
import { Notice } from "@/components/ui/notice";
import { BookmarkButton } from "@/components/chat/bookmark-button";
import { photoSrc } from "@/components/chat/types";
import { useSavedPlaces, type SavedItem, type SavedKind } from "@/api/AccountApi";

const FILTERS: { key: SavedKind | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "place", label: "Places" },
  { key: "restaurant", label: "Restaurants" },
  { key: "hotel", label: "Hotels" },
];
const ICON = { place: Landmark, restaurant: Utensils, hotel: BedDouble };

function SavedCard({ item }: { item: SavedItem }) {
  const e = item.entity ?? ({ name: item.name } as SavedItem["entity"]);
  const src = photoSrc(e.photos, e.photo_url, 400);
  const Icon = ICON[item.kind] ?? MapPin;
  const maps = e.google_maps_uri || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([item.name, e.address].filter(Boolean).join(", "))}`;
  const rating = e.rating ?? e.guest_rating;
  return (
    <li className="relative flex flex-col overflow-hidden rounded-xl border bg-card">
      {src ? (
        <img src={src} alt={`Photo of ${item.name}`} loading="lazy" className="aspect-[4/3] w-full bg-muted object-cover" />
      ) : (
        <div className="flex aspect-[4/3] w-full items-center justify-center bg-muted" aria-hidden="true"><Icon className="size-6 text-gray-strong" /></div>
      )}
      <BookmarkButton entity={{ ...e, id: item.entity_id, name: item.name }} kind={item.kind} className="absolute right-2 top-2" />
      <div className="flex flex-1 flex-col gap-1 p-3">
        <p className="text-meta font-semibold uppercase tracking-wide text-muted-foreground">{item.kind === "place" ? "Place" : item.kind === "restaurant" ? "Restaurant" : "Hotel"}</p>
        <h2 className="font-display text-base font-semibold leading-snug">{item.name}</h2>
        {rating != null && <p className="text-meta tabular text-ink">★ {Number(rating).toFixed(1)}</p>}
        {e.address && <p className="line-clamp-2 text-meta text-muted-foreground">{e.address}</p>}
        <div className="mt-auto flex flex-wrap gap-x-3 pt-1 text-sm font-medium">
          <a href={maps} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-9 items-center gap-1 text-raspberry hover:text-raspberry-hover pointer-coarse:min-h-11">
            <MapPin className="size-3.5" aria-hidden="true" />Google Maps<span className="sr-only"> (opens in a new tab)</span>
          </a>
          {item.conversation_id && (
            <Link to={`/chat/${item.conversation_id}`} className="inline-flex min-h-9 items-center text-raspberry hover:text-raspberry-hover pointer-coarse:min-h-11">Open trip</Link>
          )}
        </div>
      </div>
    </li>
  );
}

/** Bookmarked places, restaurants and hotels (GET /api/saved-places). */
export default function SavedPage() {
  const { data, isLoading, isError } = useSavedPlaces();
  const [filter, setFilter] = useState<SavedKind | "all">("all");
  const items = (data ?? []).filter((i) => filter === "all" || i.kind === filter);
  return (
    <div className="mx-auto w-full max-w-5xl px-gutter py-10 md:py-14">
      <h1 className="flex items-center gap-2 font-display text-title font-semibold">
        <Bookmark className="size-5 text-raspberry" aria-hidden="true" />
        Saved
      </h1>
      <p className="mt-1 text-muted-foreground">Places, restaurants and hotels you bookmarked from your trips.</p>
      <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Filter saved items">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            aria-pressed={filter === f.key}
            onClick={() => setFilter(f.key)}
            className={cn("min-h-9 rounded-full border px-3 text-sm font-medium pointer-coarse:min-h-11", filter === f.key ? "border-raspberry bg-raspberry-tint" : "hover:bg-muted")}
          >
            {f.label}
            <span className="ml-1 text-muted-foreground tabular">{(data ?? []).filter((i) => f.key === "all" || i.kind === f.key).length}</span>
          </button>
        ))}
      </div>
      {isError && <Notice tone="error" className="mt-6" title="Couldn't load your saved places" description="Check your connection and reload." />}
      {isLoading ? (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
          {[0, 1, 2].map((i) => <div key={i} className="aspect-[4/3] rounded-xl bg-muted animate-breathe" />)}
        </div>
      ) : items.length === 0 && !isError ? (
        <Notice tone="info" className="mt-6" title="Nothing saved yet" description="Tap the bookmark on any place, restaurant or hotel card to keep it here." />
      ) : (
        <ul className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((i) => <SavedCard key={i.id} item={i} />)}
        </ul>
      )}
    </div>
  );
}
