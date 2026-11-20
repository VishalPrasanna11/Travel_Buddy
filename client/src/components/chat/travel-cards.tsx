import { useState } from "react"
import { displayLocale } from "@/lib/format"
import {
  AirVent, BedDouble, Briefcase, ChevronDown, ChevronLeft, ChevronRight, Coffee, Dumbbell, ExternalLink, Luggage,
  Car, ParkingCircle, PawPrint, Plane, Sparkles, UtensilsCrossed, Waves, Wifi, Wine, Accessibility, Shirt, Loader2,
  type LucideIcon,
} from "lucide-react"
import { toast } from "sonner"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { bookEntity, useApiToken, ApiError } from "@/api/ConversationsApi"
import type { CarRental, Flight, FlightSegment, Hotel, Price } from "./types"
import { BookmarkButton } from "./bookmark-button"

/**
 * Flight, hotel and car cards. Times are shown in each airport's local time
 * (the API sends ISO times with that airport's UTC offset), never converted
 * to the browser's zone. Every number comes from the API response.
 */

export function money(p?: Price, amount?: number) {
  if (!p) return null
  const value = amount ?? p.amount
  try {
    return new Intl.NumberFormat(displayLocale(), { style: "currency", currency: p.currency || "USD", maximumFractionDigits: value >= 100 ? 0 : 2 }).format(value)
  } catch {
    return `${p.currency} ${value}`
  }
}

/** "13:21" and "Mar 12" from an ISO time, in the time's own offset. */
function localParts(iso?: string) {
  if (!iso) return null
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso)
  if (!m) return null
  const [, y, mo, d, h, mi] = m
  const date = new Date(Date.UTC(+y, +mo - 1, +d, 12))
  return {
    time: `${h}:${mi}`,
    date: date.toLocaleDateString(displayLocale(), { month: "short", day: "numeric", timeZone: "UTC" }),
    day: `${y}-${mo}-${d}`,
    offset: /([+-]\d{2}:\d{2}|Z)$/.exec(iso)?.[1],
  }
}

function dayDiff(a?: string, b?: string) {
  const pa = localParts(a), pb = localParts(b)
  if (!pa || !pb) return 0
  return Math.round((Date.parse(pb.day) - Date.parse(pa.day)) / 86_400_000)
}

function hm(minutes?: number) {
  if (!minutes && minutes !== 0) return null
  const h = Math.floor(minutes / 60), m = minutes % 60
  return h ? `${h}h${m ? ` ${m}m` : ""}` : `${m}m`
}

function Time({ iso, airport }: { iso?: string; airport?: string }) {
  const p = localParts(iso)
  if (!p) return <span className="font-semibold text-ink">{airport}</span>
  return (
    <span className="tabular">
      <time dateTime={iso} className="font-display text-lg font-semibold text-ink" title={p.offset ? `Local time (UTC${p.offset === "Z" ? "" : p.offset})` : "Local time"}>
        {p.time}
      </time>{" "}
      <span className="font-medium text-ink">{airport}</span>
      <span className="block text-meta text-muted-foreground">{p.date}</span>
    </span>
  )
}

export function BookButton({ entityId, label = "Book", disabled }: { entityId?: string; label?: string; disabled?: boolean }) {
  const getToken = useApiToken()
  const [busy, setBusy] = useState(false)
  if (!entityId) return null
  const go = async () => {
    // Open the tab now (inside the click) so popup blockers allow it, then point it at checkout.
    const tab = window.open("", "_blank")
    setBusy(true)
    try {
      const { url } = await bookEntity(entityId, await getToken())
      if (tab) {
        tab.opener = null
        tab.location.href = url
      } else {
        window.location.href = url
      }
    } catch (err) {
      tab?.close()
      const msg = err instanceof ApiError ? err.message : "Couldn't open checkout. Try again."
      toast.error(msg)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Button size="sm" onClick={go} disabled={disabled || busy} aria-busy={busy || undefined}>
      {busy ? <Loader2 className="motion-safe:animate-spin" aria-hidden="true" /> : <ExternalLink aria-hidden="true" />}
      {label}<span className="sr-only"> (opens the provider's checkout in a new tab)</span>
    </Button>
  )
}

function Leg({ label, segments, total, stops }: { label: string; segments: FlightSegment[]; total?: number; stops?: number }) {
  const [open, setOpen] = useState(false)
  if (!segments.length) return null
  const first = segments[0], last = segments[segments.length - 1]
  const plus = dayDiff(first.departure.at, last.arrival.at)
  const via = segments.slice(0, -1).map((s) => s.arrival.airport).filter(Boolean)
  return (
    <div>
      <p className="mb-1 text-meta font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3">
        <Time iso={first.departure.at} airport={first.departure.airport} />
        <div className="min-w-0 text-center text-meta text-muted-foreground">
          <span className="block tabular">{hm(total)}</span>
          <span className="relative my-1 block h-px bg-gray-strong" aria-hidden="true">
            {via.map((_, i) => <span key={i} className="absolute top-1/2 size-1.5 -translate-y-1/2 rounded-full bg-amber-ink" style={{ left: `${((i + 1) / (via.length + 1)) * 100}%` }} />)}
          </span>
          <span className="block">{stops ? `${stops} stop${stops > 1 ? "s" : ""} · ${via.join(", ")}` : "Nonstop"}</span>
        </div>
        <span className="text-right">
          <Time iso={last.arrival.at} airport={last.arrival.airport} />
          {plus > 0 && <span className="text-meta font-semibold text-amber-ink">+{plus} day{plus > 1 ? "s" : ""}</span>}
        </span>
      </div>
      {segments.length > 0 && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="mt-1 inline-flex min-h-8 items-center gap-1 text-meta font-medium text-raspberry hover:text-raspberry-hover pointer-coarse:min-h-11"
        >
          <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden="true" />
          {open ? "Hide" : "Show"} flight details
        </button>
      )}
      {open && (
        <ol className="mt-2 space-y-2 border-l border-border pl-3">
          {segments.map((s, i) => (
            <li key={i} className="text-sm">
              <p className="font-medium text-ink">
                {s.carrier_name || s.carrier} {s.flight_number}
                <span className="ml-2 text-meta font-normal text-muted-foreground">{[s.cabin_class, s.fare_family].filter(Boolean).join(" · ")}</span>
              </p>
              <p className="text-meta text-muted-foreground tabular">
                {localParts(s.departure.at)?.time} {s.departure.airport}{s.departure.airport_name ? ` (${s.departure.airport_name})` : ""} → {localParts(s.arrival.at)?.time} {s.arrival.airport}{s.arrival.airport_name ? ` (${s.arrival.airport_name})` : ""} · {hm(s.duration_minutes)}
              </p>
              {(s.checked_baggage || s.cabin_baggage) && (
                <p className="text-meta text-muted-foreground">{[s.cabin_baggage, s.checked_baggage].filter(Boolean).join(" · ")}</p>
              )}
              {s.layover_minutes != null && (
                <p className={cn("mt-1 rounded-md px-2 py-1 text-meta", s.layover_minutes < 60 ? "bg-danger-tint text-ink" : "bg-muted text-muted-foreground")}>
                  {hm(s.layover_minutes)} layover in {s.arrival.airport}{s.layover_minutes < 60 ? " (tight connection)" : ""}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

export function FlightCard({ f }: { f: Flight }) {
  const total = money(f.price, f.price?.total ?? f.price?.amount)
  const per = f.price?.per_traveler != null && f.price.per_traveler !== f.price.total ? money(f.price, f.price.per_traveler) : null
  return (
    <li className="rounded-xl border bg-card p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-flight-tint"><Plane className="size-4 text-flight-ink" aria-hidden="true" /></span>
          <div className="min-w-0">
            <p className="truncate font-semibold">{f.carrier_name || f.carrier || "Flight"}</p>
            <p className="text-meta text-muted-foreground">{[f.cabin_class, f.fare_family?.toLowerCase()].filter(Boolean).join(" · ")}</p>
          </div>
        </div>
        {total && (
          <div className="text-right">
            <p className="font-display text-lg font-semibold tabular">{total}</p>
            <p className="text-meta text-muted-foreground">{per ? `${per} per traveler · ` : ""}taxes incl.</p>
          </div>
        )}
      </div>
      <div className="space-y-4">
        <Leg label={f.return_segments?.length ? "Outbound" : "Flight"} segments={f.segments ?? []} total={f.duration_minutes} stops={f.stops} />
        {!!f.return_segments?.length && <Leg label="Return" segments={f.return_segments} total={f.return_duration_minutes} stops={f.return_stops} />}
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <div className="flex flex-wrap gap-1.5">
          {f.baggage?.cabin && <Badge variant="neutral"><Briefcase aria-hidden="true" />{f.baggage.cabin}</Badge>}
          {f.baggage?.checked && <Badge variant={/no checked/i.test(f.baggage.checked) ? "estimate" : "neutral"}><Luggage aria-hidden="true" />{f.baggage.checked}</Badge>}
          {f.refundable === false && <Badge variant="neutral">Non-refundable</Badge>}
        </div>
        {f.bookable && <BookButton entityId={f.id} />}
        {!f.bookable && f.booking_url && (
          <a href={f.booking_url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-raspberry">Book<span className="sr-only"> (opens in a new tab)</span></a>
        )}
      </div>
    </li>
  )
}

const AMENITY_ICON: Record<string, { Icon: LucideIcon; label: string }> = {
  WIFI: { Icon: Wifi, label: "Wi-Fi" },
  POOL: { Icon: Waves, label: "Pool" },
  SPA: { Icon: Sparkles, label: "Spa" },
  GYM: { Icon: Dumbbell, label: "Gym" },
  PARKING: { Icon: ParkingCircle, label: "Parking" },
  BREAKFAST: { Icon: Coffee, label: "Breakfast" },
  RESTAURANT: { Icon: UtensilsCrossed, label: "Restaurant" },
  BAR: { Icon: Wine, label: "Bar" },
  AIR_CONDITIONING: { Icon: AirVent, label: "Air conditioning" },
  AIRPORT_SHUTTLE: { Icon: Car, label: "Airport shuttle" },
  PETS_ALLOWED: { Icon: PawPrint, label: "Pets allowed" },
  ACCESSIBLE: { Icon: Accessibility, label: "Accessible" },
  LAUNDRY: { Icon: Shirt, label: "Laundry" },
}

function Carousel({ hotel }: { hotel: Hotel }) {
  const photos = (hotel.photos ?? []).filter((p) => p.url)
  const [i, setI] = useState(0)
  const [failed, setFailed] = useState<Set<number>>(new Set())
  const usable = photos.filter((_, idx) => !failed.has(idx))
  if (!usable.length) {
    return (
      <div className="flex aspect-[4/3] w-full items-center justify-center bg-stay-tint sm:w-56 sm:shrink-0" aria-hidden="true">
        <BedDouble className="size-6 text-stay-ink" />
      </div>
    )
  }
  const idx = i % photos.length
  const step = (d: number) => setI((v) => (v + d + photos.length) % photos.length)
  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden bg-muted sm:w-56 sm:shrink-0" aria-roledescription="carousel" aria-label={`Photos of ${hotel.name}`}>
      <img
        key={idx}
        src={photos[idx].url}
        alt={`${hotel.name}, photo ${idx + 1} of ${photos.length}`}
        loading="lazy"
        decoding="async"
        onError={() => { setFailed((s) => new Set(s).add(idx)); step(1) }}
        className="size-full object-cover animate-fade-in"
      />
      {photos.length > 1 && (
        <>
          <button type="button" onClick={() => step(-1)} aria-label="Previous photo" className="absolute left-1.5 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-black/50 text-white hover:bg-black/70 pointer-coarse:size-10">
            <ChevronLeft className="size-4" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => step(1)} aria-label="Next photo" className="absolute right-1.5 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-black/50 text-white hover:bg-black/70 pointer-coarse:size-10">
            <ChevronRight className="size-4" aria-hidden="true" />
          </button>
          <span className="absolute bottom-1.5 right-1.5 rounded bg-black/55 px-1.5 text-[0.6875rem] text-white tabular">{idx + 1}/{photos.length}</span>
        </>
      )}
    </div>
  )
}

export function HotelCard({ h }: { h: Hotel }) {
  const total = money(h.price, h.price?.total ?? h.price?.amount)
  const nightly = money(h.nightly_price)
  const was = h.price?.published && h.price.published > (h.price.total ?? h.price.amount) ? money(h.price, h.price.published) : null
  const amenities = (h.amenities ?? []).filter((a) => AMENITY_ICON[a]).slice(0, 7)
  return (
    <li className="relative flex flex-col overflow-hidden rounded-xl border bg-card sm:flex-row">
      <Carousel hotel={h} />
      <BookmarkButton entity={h} kind="hotel" className="absolute left-2 top-2" />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5 p-3">
        <div className="flex flex-wrap items-start justify-between gap-x-3">
          <div className="min-w-0">
            <p className="font-semibold leading-snug [overflow-wrap:anywhere]">{h.name}</p>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-meta text-muted-foreground">
              {h.star_rating != null && (
                <span className="tabular" aria-label={`${h.star_rating}-star hotel`}>
                  <span aria-hidden="true" className="text-amber-ink">{"★".repeat(Math.round(h.star_rating))}</span> {h.star_rating}-star
                </span>
              )}
              {h.guest_rating != null && (
                <span className="tabular">
                  <span className="rounded bg-success-tint px-1 font-semibold text-ink">{h.guest_rating}</span> guests{h.review_count ? ` · ${h.review_count.toLocaleString(displayLocale())} reviews` : ""}
                </span>
              )}
            </div>
          </div>
          {nightly ? (
            <div className="text-right">
              <p className="font-display text-lg font-semibold tabular">{nightly}<span className="text-meta font-normal text-muted-foreground"> /night</span></p>
              <p className="text-meta text-muted-foreground tabular">{was && <s className="mr-1">{was}</s>}{total} total{h.nights ? ` · ${h.nights} night${h.nights > 1 ? "s" : ""}` : ""}</p>
            </div>
          ) : total ? (
            <p className="font-display text-lg font-semibold tabular">{total}<span className="block text-meta font-normal text-muted-foreground">total</span></p>
          ) : null}
        </div>
        {h.address && <p className="text-meta text-muted-foreground">{h.address}{h.distance_km != null ? ` · ${h.distance_km.toFixed(1)} km from centre` : ""}</p>}
        {amenities.length > 0 && (
          <ul className="flex flex-wrap gap-1.5" aria-label="Amenities">
            {amenities.map((a) => {
              const { Icon, label } = AMENITY_ICON[a]
              return (
                <li key={a} className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-meta text-ink" title={label}>
                  <Icon className="size-3.5 text-stay-ink" aria-hidden="true" />{label}
                </li>
              )
            })}
          </ul>
        )}
        <div className="mt-auto flex flex-wrap items-end justify-between gap-2 pt-1">
          <div className="text-meta">
            {h.cancellation_policy && <p className={h.refundable ? "font-medium text-success-ink" : "text-muted-foreground"}>{h.cancellation_policy}</p>}
            {(h.check_in_time || h.check_out_time) && <p className="text-muted-foreground tabular">Check-in {h.check_in_time ?? "—"} · Check-out {h.check_out_time ?? "—"}</p>}
          </div>
          {h.bookable && <BookButton entityId={h.id} />}
        </div>
      </div>
    </li>
  )
}

export function CarCard({ c }: { c: CarRental }) {
  const price = money(c.price)
  const pick = localParts(c.pickup_at), drop = localParts(c.dropoff_at)
  return (
    <li className="flex items-start gap-3 rounded-xl border bg-card p-3">
      {c.image_url ? (
        <img src={c.image_url} alt="" loading="lazy" className="h-16 w-24 shrink-0 rounded-md bg-muted object-contain" />
      ) : (
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-flight-tint"><Car className="size-5 text-flight-ink" aria-hidden="true" /></span>
      )}
      <div className="min-w-0 flex-1">
        <p className="font-semibold leading-snug">{c.name}</p>
        <p className="text-meta text-muted-foreground">{[c.vendor, c.category, c.transmission, c.seats ? `${c.seats} seats` : null, c.bags ? `${c.bags} bags` : null].filter(Boolean).join(" · ")}</p>
        {(c.mileage || c.free_cancellation) && (
          <p className="text-meta text-success-ink">{[c.mileage, c.free_cancellation ? "Free cancellation" : null].filter(Boolean).join(" · ")}</p>
        )}
        {c.pickup_location && <p className="text-meta text-muted-foreground">{c.pickup_location}{pick ? ` · ${pick.date} ${pick.time}` : ""}{drop ? ` → ${drop.date} ${drop.time}` : ""}</p>}
      </div>
      <div className="flex flex-col items-end gap-1.5">
        {price && <p className="font-semibold tabular">{price}<span className="block text-right text-meta font-normal text-muted-foreground">total</span></p>}
        {c.bookable && <BookButton entityId={c.id} />}
      </div>
    </li>
  )
}
