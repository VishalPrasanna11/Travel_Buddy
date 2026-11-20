import { useId, useState } from "react"
import { BedDouble, Clock, Landmark, MapPin, Plane, Star, Utensils } from "lucide-react"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { attractionsOf, type Flight, type Hotel, type Place, type ResponseData } from "./types"

/**
 * Structured results that came back with an answer. Everything shown here is
 * a field the API returned. Missing fields are left out, never guessed.
 */

const nf = new Intl.NumberFormat(undefined)

function mapsUrl(p: Place) {
  const q = [p.name, p.address].filter(Boolean).join(", ")
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`
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
      <PlacePhoto src={place.photo_url} name={place.name} Icon={Icon} />
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
        {shown.map((p, i) => <PlaceCard key={`${p.name}-${i}`} place={p} Icon={icon} />)}
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
  const price = f.price?.total ? `${f.price.currency ? `${f.price.currency} ` : ""}${f.price.total}` : null
  return (
    <li className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 rounded-xl border bg-card p-3 sm:grid-cols-[minmax(8rem,1fr)_2fr_auto] sm:items-center">
      <div className="flex min-w-0 items-center gap-2">
        <Plane className="size-4 shrink-0 text-flight-ink" aria-hidden="true" />
        <span className="truncate font-semibold">{f.carrierName || f.carrier || "Flight"}</span>
        {f.flightNumber && <span className="text-meta text-muted-foreground">{f.flightNumber}</span>}
      </div>
      {price && <div className="text-right font-semibold tabular sm:order-last">{price}</div>}
      <div className="col-span-2 flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground tabular sm:col-span-1">
        <span><span className="font-medium text-ink">{f.departure?.iataCode}</span> {fmtTime(f.departure?.at)}</span>
        <span aria-hidden="true">→</span>
        <span className="sr-only">to</span>
        <span><span className="font-medium text-ink">{f.arrival?.iataCode}</span> {fmtTime(f.arrival?.at)}</span>
        {f.duration && (
          <span className="inline-flex items-center gap-1"><Clock className="size-3.5" aria-hidden="true" />{fmtDuration(f.duration)}</span>
        )}
        {f.cabinClass && <Badge variant="flight" className="capitalize">{f.cabinClass.toLowerCase()}</Badge>}
      </div>
    </li>
  )
}

function HotelRow({ h }: { h: Hotel }) {
  const where = [h.address?.cityName, h.address?.countryCode].filter(Boolean).join(", ")
  return (
    <li className="flex items-start gap-3 rounded-xl border bg-card p-3">
      <span className="mt-0.5 inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-stay-tint">
        <BedDouble className="size-4 text-stay-ink" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold leading-snug [overflow-wrap:anywhere]">{h.name}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-meta text-muted-foreground">
          {h.rating != null && h.rating !== "" && <span className="tabular">{h.rating}-star hotel</span>}
          {where && <span>{where}</span>}
        </div>
      </div>
    </li>
  )
}

export function ResultCards({ data }: { data?: ResponseData }) {
  if (!data) return null
  const flights = data.flights?.data ?? []
  const hotels = data.hotels?.data ?? []
  const attractions = attractionsOf(data)
  const restaurants = data.restaurants ?? []
  if (!flights.length && !hotels.length && !attractions.length && !restaurants.length) return null

  return (
    <div className={cn("max-w-3xl")}>
      {flights.length > 0 && (
        <Section title="Flights" icon={Plane} count={flights.length}>
          <ul className="space-y-2">{flights.slice(0, 8).map((f, i) => <FlightRow key={f.id ?? i} f={f} />)}</ul>
        </Section>
      )}
      {hotels.length > 0 && (
        <Section title="Hotels" icon={BedDouble} count={hotels.length}>
          <ul className="space-y-2">{hotels.slice(0, 8).map((h, i) => <HotelRow key={h.hotelId ?? i} h={h} />)}</ul>
        </Section>
      )}
      <PlaceSection title="Places to see" places={attractions} icon={Landmark} />
      <PlaceSection title="Places to eat" places={restaurants} icon={Utensils} />
    </div>
  )
}
