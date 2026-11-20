import { useId, useState } from "react"
import { BedDouble, Clock, Landmark, MapPin, Plane, Star, Utensils } from "lucide-react"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Notice } from "@/components/ui/notice"
import { attractionsOf, flightsOf, hotelsOf, restaurantsOf, type Flight, type Hotel, type Place, type Price, type ResponseData, type SectionKey, type SectionStatus } from "./types"

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

export function fmtPrice(p?: Price, opts: { amount?: number } = {}) {
  if (!p) return null
  const value = opts.amount ?? p.amount
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: p.currency || "USD", maximumFractionDigits: value >= 100 ? 0 : 2 }).format(value)
  } catch {
    return `${p.currency} ${value}`
  }
}

function photoOf(p: Place) {
  return p.photo_url
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

function PlacePhoto({ src, name, Icon }: { src?: string; name: string; Icon: typeof MapPin }) {
  const [failed, setFailed] = useState(false)
  if (!src || failed) {
    return (
      <div className="flex aspect-[4/3] w-full items-center justify-center bg-muted" aria-hidden="true">
        <Icon className="size-6 text-gray-strong" />
      </div>
    )
  }
  return (
    <img
      src={src}
      alt={`Photo of ${name}`}
      width={400}
      height={300}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      className="aspect-[4/3] w-full bg-muted object-cover"
    />
  )
}

function PlaceCard({ place, Icon }: { place: Place; Icon: typeof MapPin }) {
  return (
    <li className="group overflow-hidden rounded-xl border bg-card transition-colors hover:border-gray-strong">
      <PlacePhoto src={photoOf(place)} name={place.name} Icon={Icon} />
      <div className="space-y-1 p-3">
        <h5 className="line-clamp-2 font-display text-base font-semibold leading-snug" title={place.name}>
          {place.name}
        </h5>
        <Rating value={place.rating} count={place.total_ratings} />
        {place.address && <p className="line-clamp-2 text-meta text-muted-foreground">{place.address}</p>}
        <a
          href={mapsUrl(place)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-9 items-center gap-1 text-sm font-medium text-raspberry hover:text-raspberry-hover pointer-coarse:min-h-11"
        >
          <MapPin className="size-3.5" aria-hidden="true" />
          Open in Google Maps<span className="sr-only"> (opens in a new tab)</span>
        </a>
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

function fmtTime(iso?: string) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return (
    <time dateTime={iso}>
      {d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
    </time>
  )
}

function fmtDuration(iso?: string) {
  if (!iso) return null
  const m = /^PT(?:(\d+)H)?(?:(\d+)M)?$/.exec(iso)
  return m ? `${m[1] ? `${m[1]}h ` : ""}${m[2] ? `${m[2]}m` : ""}`.trim() : iso
}

function FlightRow({ f }: { f: Flight }) {
  const price = fmtPrice(f.price)
  const segs = f.segments ?? []
  const number = segs.map((s) => s.flight_number).filter(Boolean).join(" · ")
  return (
    <li className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 rounded-xl border bg-card p-3 sm:grid-cols-[minmax(8rem,1fr)_2fr_auto] sm:items-center">
      <div className="flex min-w-0 items-center gap-2">
        <Plane className="size-4 shrink-0 text-flight-ink" aria-hidden="true" />
        <span className="truncate font-semibold">{f.carrier_name || f.carrier || "Flight"}</span>
        {number && <span className="text-meta text-muted-foreground">{number}</span>}
      </div>
      {price && <div className="text-right font-semibold tabular sm:order-last">{price}</div>}
      <div className="col-span-2 flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground tabular sm:col-span-1">
        <span><span className="font-medium text-ink">{f.origin}</span> {fmtTime(f.departure_at)}</span>
        <span aria-hidden="true">→</span>
        <span className="sr-only">to</span>
        <span><span className="font-medium text-ink">{f.destination}</span> {fmtTime(f.arrival_at)}</span>
        {(f.duration || f.duration_minutes) && (
          <span className="inline-flex items-center gap-1"><Clock className="size-3.5" aria-hidden="true" />{fmtDuration(f.duration) ?? `${Math.floor(f.duration_minutes! / 60)}h ${f.duration_minutes! % 60}m`}</span>
        )}
        <span>{f.stops ? `${f.stops} stop${f.stops > 1 ? "s" : ""}` : "Nonstop"}</span>
        {f.cabin_class && <Badge variant="flight" className="capitalize">{f.cabin_class.toLowerCase()}</Badge>}
      </div>
    </li>
  )
}

function HotelRow({ h }: { h: Hotel }) {
  const price = fmtPrice(h.price)
  return (
    <li className="flex items-start gap-3 rounded-xl border bg-card p-3">
      <span className="mt-0.5 inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-stay-tint">
        <BedDouble className="size-4 text-stay-ink" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold leading-snug [overflow-wrap:anywhere]">{h.name}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-meta text-muted-foreground">
          {h.star_rating != null && <span className="tabular">{h.star_rating}-star hotel</span>}
          {h.guest_rating != null && <span className="tabular">Guests {h.guest_rating}</span>}
          {h.address && <span>{h.address}</span>}
        </div>
      </div>
      {price && <div className="text-right font-semibold tabular">{price}<span className="block text-meta font-normal text-muted-foreground">total</span></div>}
    </li>
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
        <Section title="Flights" icon={Plane} count={flights.length}>
          <ul className="space-y-2">{flights.slice(0, 8).map((f, i) => <FlightRow key={f.id ?? i} f={f} />)}</ul>
        </Section>
      )}
      {hotels.length > 0 && (
        <Section title="Hotels" icon={BedDouble} count={hotels.length}>
          <ul className="space-y-2">{hotels.slice(0, 8).map((h, i) => <HotelRow key={h.id ?? i} h={h} />)}</ul>
        </Section>
      )}
      <PlaceSection title="Places to see" places={attractions} icon={Landmark} />
      <PlaceSection title="Places to eat" places={restaurants} icon={Utensils} />
      <SectionNotices sections={data.sections} />
    </div>
  )
}
