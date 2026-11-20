import { useId, useState } from "react"
import { AlertTriangle, BedDouble, Clock, ExternalLink, Globe, Landmark, MapPin, Plane, Star, Utensils } from "lucide-react"

import { cn } from "@/lib/utils"
import { Notice } from "@/components/ui/notice"
import { FlightCard, HotelCard } from "./travel-cards"
import { attractionsOf, flightsOf, hotelsOf, photoSrc, restaurantsOf, type Photo, type Place, type ResponseData, type SectionKey, type SectionStatus } from "./types"

/**
 * Structured results that came back with an answer. Everything shown here is
 * a field the API returned. Missing fields are left out, never guessed.
 */

const nf = new Intl.NumberFormat(undefined)

function mapsUrl(p: Place) {
  if (p.google_maps_uri) return p.google_maps_uri
  const q = [p.name, p.address].filter(Boolean).join(", ")
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}${p.place_id ? `&query_place_id=${p.place_id}` : ""}`
}

const PRICE_LABEL = ["Free", "$", "$$", "$$$", "$$$$"]
const PRICE_NAME = ["free", "inexpensive", "moderate", "expensive", "very expensive"]

/** "Closed Mondays" from Google's weekday descriptions. */
function closedDays(p: Place) {
  return (p.opening_hours?.weekday_descriptions ?? [])
    .filter((d) => /:\s*closed/i.test(d))
    .map((d) => d.split(":")[0])
}

function todayHours(p: Place) {
  const list = p.opening_hours?.weekday_descriptions
  if (!list?.length) return null
  // Google lists Monday first.
  const idx = (new Date().getDay() + 6) % 7
  return list[idx]?.split(/:\s(.+)/)[1] ?? null
}

function Rating({ value, count }: { value?: number | string; count?: number }) {
  const n = typeof value === "string" ? Number.parseFloat(value) : value
  if (n == null || Number.isNaN(n)) return null
  return (
    <span className="inline-flex items-center gap-1 text-meta tabular">
      <Star className="size-3.5 fill-amber text-amber-ink" aria-hidden="true" />
      <span className="font-semibold text-ink">{n.toFixed(1)}</span>
      {count != null && <span className="text-muted-foreground">({nf.format(count)} reviews)</span>}
      <span className="sr-only"> out of 5</span>
    </span>
  )
}

function PlacePhoto({ photos, legacy, name, Icon }: { photos?: Photo[]; legacy?: string; name: string; Icon: typeof MapPin }) {
  const [failed, setFailed] = useState(false)
  const src = photoSrc(photos, legacy, 480)
  const photo = photos?.find((p) => p.ref || p.url)
  const credit = photo?.attributions?.[0]
  if (!src || failed) {
    return (
      <div className="flex aspect-[4/3] w-full items-center justify-center bg-muted" aria-hidden="true">
        <Icon className="size-6 text-gray-strong" />
      </div>
    )
  }
  return (
    <figure className="relative">
      <img
        src={src}
        alt={`Photo of ${name}`}
        width={photo?.width ? Math.min(photo.width, 480) : 400}
        height={photo?.width && photo?.height ? Math.round((Math.min(photo.width, 480) / photo.width) * photo.height) : 300}
        loading="lazy"
        decoding="async"
        onError={() => setFailed(true)}
        className="aspect-[4/3] w-full bg-muted object-cover"
      />
      {credit?.name && (
        <figcaption className="absolute bottom-1 right-1 max-w-[85%] truncate rounded bg-black/55 px-1.5 py-0.5 text-[0.6875rem] text-white">
          {credit.uri ? (
            <a href={credit.uri} target="_blank" rel="noopener noreferrer" className="hover:underline">Photo: {credit.name}</a>
          ) : (
            <>Photo: {credit.name}</>
          )}
        </figcaption>
      )}
    </figure>
  )
}

function PlaceCard({ place, Icon }: { place: Place; Icon: typeof MapPin }) {
  const closed = closedDays(place)
  const hours = todayHours(place)
  return (
    <li className="group flex flex-col overflow-hidden rounded-xl border bg-card transition-colors hover:border-gray-strong">
      <PlacePhoto photos={place.photos} legacy={place.photo_url} name={place.name} Icon={Icon} />
      <div className="flex flex-1 flex-col gap-1 p-3">
        <h5 className="line-clamp-2 font-display text-base font-semibold leading-snug" title={place.name}>
          {place.name}
        </h5>
        <div className="flex flex-wrap items-center gap-x-2">
          <Rating value={place.rating} count={place.total_ratings} />
          {place.price_level != null && (
            <span className="text-meta font-medium text-ink tabular" title={`Price level: ${PRICE_NAME[place.price_level]}`}>
              {PRICE_LABEL[place.price_level]}<span className="sr-only"> ({PRICE_NAME[place.price_level]})</span>
            </span>
          )}
        </div>
        {place.editorial_summary && <p className="line-clamp-3 text-sm text-ink">{place.editorial_summary}</p>}
        {hours && <p className="text-meta text-muted-foreground"><Clock className="mr-1 inline size-3" aria-hidden="true" />Today: {hours}</p>}
        {closed.length > 0 && closed.length < 7 && (
          <p className="text-meta font-medium text-amber-ink">
            <AlertTriangle className="mr-1 inline size-3" aria-hidden="true" />Closed {closed.join(", ")}
          </p>
        )}
        {place.address && <p className="line-clamp-2 text-meta text-muted-foreground">{place.address}</p>}
        <div className="mt-auto flex flex-wrap gap-x-3 pt-1">
          <a
            href={mapsUrl(place)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-9 items-center gap-1 text-sm font-medium text-raspberry hover:text-raspberry-hover pointer-coarse:min-h-11"
          >
            <MapPin className="size-3.5" aria-hidden="true" />
            Google Maps<span className="sr-only"> (opens in a new tab)</span>
          </a>
          {place.website && (
            <a
              href={place.website}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-9 items-center gap-1 text-sm font-medium text-raspberry hover:text-raspberry-hover pointer-coarse:min-h-11"
            >
              <Globe className="size-3.5" aria-hidden="true" />
              Website<ExternalLink className="size-3" aria-hidden="true" /><span className="sr-only"> (opens in a new tab)</span>
            </a>
          )}
        </div>
      </div>
    </li>
  )
}

function Section({ title, icon: Icon, count, children, note }: { title: string; icon: typeof MapPin; count: number; children: React.ReactNode; note?: string }) {
  const id = useId()
  return (
    <section aria-labelledby={id} className="mt-8">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
        <h4 id={id} className="flex items-center gap-2 whitespace-nowrap text-heading font-semibold">
          <Icon className="size-4 text-raspberry" aria-hidden="true" />
          {title}
          <span className="text-sm font-normal text-muted-foreground tabular">{count}</span>
        </h4>
        {note && <span className="text-meta text-muted-foreground">{note}</span>}
      </div>
      {children}
    </section>
  )
}

const INITIAL = 4

function PlaceSection({ title, places, icon }: { title: string; places: Place[]; icon: typeof MapPin }) {
  const [expanded, setExpanded] = useState(false)
  const listId = useId()
  if (!places.length) return null
  const shown = expanded ? places : places.slice(0, INITIAL)
  return (
    <Section title={title} icon={icon} count={places.length} note="Photos and ratings from Google">
      <ul id={listId} className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2">
        {shown.map((p, i) => <PlaceCard key={p.id ?? `${p.name}-${i}`} place={p} Icon={icon} />)}
      </ul>
      {places.length > INITIAL && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-controls={listId}
          className="mt-3 inline-flex min-h-10 items-center rounded-md px-3 text-sm font-medium text-raspberry hover:bg-accent pointer-coarse:min-h-11"
        >
          {expanded ? "Show fewer" : `Show all ${places.length}`}
        </button>
      )}
    </Section>
  )
}

/** "Prices as of 9:12" freshness note. */
function asOf(iso?: string) {
  if (!iso) return undefined
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return undefined
  return `Prices as of ${d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`
}

function ExpandableList<T>({ items, initial, render }: { items: T[]; initial: number; render: (item: T, i: number) => React.ReactNode }) {
  const [expanded, setExpanded] = useState(false)
  const listId = useId()
  const shown = expanded ? items : items.slice(0, initial)
  return (
    <>
      <ul id={listId} className="space-y-3">{shown.map(render)}</ul>
      {items.length > initial && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-controls={listId}
          className="mt-3 inline-flex min-h-10 items-center rounded-md px-3 text-sm font-medium text-raspberry hover:bg-accent pointer-coarse:min-h-11"
        >
          {expanded ? "Show fewer" : `Show all ${items.length}`}
        </button>
      )}
    </>
  )
}

const SECTION_LABEL: Record<SectionKey, string> = {
  flights: "Flights", hotels: "Hotels", attractions: "Places to see", restaurants: "Places to eat", weather: "Weather", cars: "Car rentals",
}

/** "No flights that day — try Mar 13": explain empty/failed/skipped sections. */
export function SectionNotices({ sections, only }: { sections?: ResponseData["sections"]; only?: SectionKey[] }) {
  if (!sections) return null
  const rows = (Object.entries(sections) as [SectionKey, SectionStatus][])
    .filter(([k, s]) => k !== "weather" && (!only || only.includes(k)) && s && (s.status === "empty" || s.status === "failed" || s.status === "skipped"))
  if (!rows.length) return null
  return (
    <div className="mt-6 max-w-prose space-y-2">
      {rows.map(([k, s]) => (
        <Notice
          key={k}
          tone={s.status === "failed" ? "error" : "info"}
          title={s.status === "failed" ? `${SECTION_LABEL[k]} unavailable` : s.status === "skipped" ? `${SECTION_LABEL[k]} not searched` : `No ${SECTION_LABEL[k].toLowerCase()} found`}
          description={
            <>
              {s.message}
              {s.alternatives?.length ? <span className="block text-muted-foreground">Try {s.alternatives.map((d) => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })).join(" or ")}.</span> : null}
            </>
          }
        />
      ))}
    </div>
  )
}

export function ResultCards({ data }: { data?: ResponseData }) {
  if (!data) return null
  const flights = flightsOf(data)
  const hotels = hotelsOf(data)
  const attractions = attractionsOf(data)
  const restaurants = restaurantsOf(data)
  if (!flights.length && !hotels.length && !attractions.length && !restaurants.length) return <SectionNotices sections={data.sections} />

  return (
    <div className={cn("max-w-3xl")}>
      {flights.length > 0 && (
        <Section title="Flights" icon={Plane} count={flights.length} note={asOf(flights[0]?.price?.as_of ?? flights[0]?.fetched_at)}>
          <ExpandableList items={flights} initial={3} render={(f, i) => <FlightCard key={f.id ?? i} f={f} />} />
        </Section>
      )}
      {hotels.length > 0 && (
        <Section title="Hotels" icon={BedDouble} count={hotels.length} note={asOf(hotels[0]?.price?.as_of ?? hotels[0]?.fetched_at)}>
          <ExpandableList items={hotels} initial={3} render={(h, i) => <HotelCard key={h.id ?? i} h={h} />} />
        </Section>
      )}
      <PlaceSection title="Places to see" places={attractions} icon={Landmark} />
      <PlaceSection title="Places to eat" places={restaurants} icon={Utensils} />
      <SectionNotices sections={data.sections} />
    </div>
  )
}
