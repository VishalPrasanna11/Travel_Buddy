import { useId, useState } from "react"
import { displayLocale } from "@/lib/format"
import { BedDouble, CalendarDays, CalendarPlus, Car, Coffee, FileDown, Footprints, Landmark, Link2, Loader2, MapPin, Plane, StickyNote, Utensils, type LucideIcon } from "lucide-react"
import { toast } from "sonner"
import { downloadTripFile, shareTrip } from "@/api/AccountApi"
import { useApiToken } from "@/api/ConversationsApi"

import { Button } from "@/components/ui/button"
import { downloadFile, itineraryToIcs } from "@/lib/ics"
import type { Location } from "@/components/LocationContext"
import { entityIndex, type Hotel, type Itinerary, type ItineraryItem, type Place, type ResponseData } from "./types"

/**
 * Day-by-day plan from the structured itinerary (GPT-4o json_schema output).
 * Items that reference a real result (place, hotel, flight) link to it and
 * can be shown on the map; free-form items ("Stroll the riverfront") don't.
 */

const KIND_ICON: Record<ItineraryItem["kind"], { Icon: LucideIcon; tone: string }> = {
  place: { Icon: Landmark, tone: "text-raspberry" },
  restaurant: { Icon: Utensils, tone: "text-raspberry" },
  hotel: { Icon: BedDouble, tone: "text-stay-ink" },
  flight: { Icon: Plane, tone: "text-flight-ink" },
  car: { Icon: Car, tone: "text-flight-ink" },
  transit: { Icon: Footprints, tone: "text-muted-foreground" },
  free: { Icon: Coffee, tone: "text-muted-foreground" },
  note: { Icon: StickyNote, tone: "text-muted-foreground" },
}

const SLOTS: ItineraryItem["slot"][] = ["morning", "afternoon", "evening", "night"]
const SLOT_LABEL: Record<ItineraryItem["slot"], string> = { morning: "Morning", afternoon: "Afternoon", evening: "Evening", night: "Night" }

function fmtDay(date: string) {
  const d = new Date(`${date}T12:00:00`)
  return Number.isNaN(d.getTime()) ? date : d.toLocaleDateString(displayLocale(), { weekday: "long", month: "short", day: "numeric" })
}

function pinsFor(items: ItineraryItem[], index: ReturnType<typeof entityIndex>): Location[] {
  const pins: Location[] = []
  for (const item of items) {
    const hit = item.ref ? index.get(item.ref) : undefined
    const e = hit?.entity as (Place | Hotel) | undefined
    if (!e || !("location" in e) || !e.location) continue
    pins.push({
      name: e.name,
      lat: e.location.lat,
      lng: e.location.lng,
      formattedAddress: e.address,
      type: hit!.kind === "hotel" ? "secondary" : hit!.kind === "restaurant" ? "reference" : "primary",
      relevanceScore: 100,
    })
  }
  return pins
}

/** PDF download and read-only share link (server; needs the trip saved to the account). */
function TripActions({ tripId }: { tripId: string }) {
  const getToken = useApiToken()
  const [busy, setBusy] = useState<"pdf" | "share" | null>(null)
  const pdf = async () => {
    setBusy("pdf")
    try {
      await downloadTripFile(tripId, "pdf", await getToken())
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Download failed.")
    } finally {
      setBusy(null)
    }
  }
  const share = async () => {
    setBusy("share")
    try {
      const { url } = await shareTrip(tripId, await getToken())
      try {
        await navigator.clipboard.writeText(url)
        toast.success("Share link copied", { description: "Anyone with the link can view this plan (read-only)." })
      } catch {
        toast.success("Share link ready", { description: url })
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Couldn't create a share link.")
    } finally {
      setBusy(null)
    }
  }
  return (
    <>
      <Button size="sm" variant="outline" onClick={pdf} disabled={busy !== null}>
        {busy === "pdf" ? <Loader2 className="motion-safe:animate-spin" aria-hidden="true" /> : <FileDown aria-hidden="true" />}
        PDF
      </Button>
      <Button size="sm" variant="outline" onClick={share} disabled={busy !== null}>
        {busy === "share" ? <Loader2 className="motion-safe:animate-spin" aria-hidden="true" /> : <Link2 aria-hidden="true" />}
        Share
      </Button>
    </>
  )
}

export function ItineraryView({ data, onShowOnMap, tripId }: { data?: ResponseData; onShowOnMap?: (pins: Location[], label: string) => void; tripId?: string }) {
  const headingId = useId()
  const it: Itinerary | undefined = data?.itinerary
  if (!it?.days?.length) return null
  const index = entityIndex(data)

  const exportIcs = () => {
    const ics = itineraryToIcs(it, {
      describe: (item) => {
        const e = item.ref ? (index.get(item.ref)?.entity as Place | undefined) : undefined
        return e && "address" in e ? e.address : undefined
      },
    })
    const name = (it.trip.destination?.name ?? "trip").split(",")[0].trim().toLowerCase().replace(/\s+/g, "-")
    downloadFile(`travelbuddy-${name}-${it.trip.start_date}.ics`, ics, "text/calendar;charset=utf-8")
  }

  return (
    <section aria-labelledby={headingId} className="mt-8 max-w-3xl">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h4 id={headingId} className="flex items-center gap-2 text-heading font-semibold">
          <CalendarDays className="size-4 text-raspberry" aria-hidden="true" />
          Day by day
          <span className="text-sm font-normal text-muted-foreground tabular">{it.days.length} days</span>
        </h4>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={exportIcs}>
            <CalendarPlus aria-hidden="true" />
            Add to calendar
          </Button>
          {tripId && <TripActions tripId={tripId} />}
        </div>
      </div>
      {it.summary && <p className="mb-4 text-sm text-muted-foreground">{it.summary}</p>}

      <ol className="space-y-4">
        {it.days.map((day, i) => {
          const pins = pinsFor(day.items, index)
          return (
            <li key={day.date + i} className="rounded-xl border bg-card">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2.5">
                <div>
                  <p className="font-display text-base font-semibold leading-snug">
                    <span className="text-raspberry">Day {i + 1}</span> · {day.title}
                  </p>
                  <p className="text-meta text-muted-foreground">{fmtDay(day.date)}</p>
                </div>
                {onShowOnMap && pins.length > 0 && (
                  <Button size="sm" variant="ghost" onClick={() => onShowOnMap(pins, `Day ${i + 1}`)}>
                    <MapPin aria-hidden="true" />
                    Day {i + 1} on map
                  </Button>
                )}
              </div>
              <div className="space-y-3 px-4 py-3">
                {SLOTS.filter((s) => day.items.some((x) => x.slot === s)).map((slot) => (
                  <div key={slot} className="grid grid-cols-[5.5rem_1fr] gap-x-3">
                    <p className="pt-0.5 text-meta font-semibold uppercase tracking-wide text-muted-foreground">{SLOT_LABEL[slot]}</p>
                    <ul className="relative space-y-2 border-l border-border pl-4">
                      {day.items.filter((x) => x.slot === slot).map((item, j) => {
                        const { Icon, tone } = KIND_ICON[item.kind] ?? KIND_ICON.note
                        const linked = item.ref ? index.get(item.ref) : undefined
                        const rating = linked && "rating" in linked.entity ? (linked.entity as Place).rating : undefined
                        return (
                          <li key={j} className="relative">
                            <span className="absolute -left-[1.4rem] top-1 inline-flex size-4 items-center justify-center rounded-full bg-background" aria-hidden="true">
                              <Icon className={`size-3.5 ${tone}`} />
                            </span>
                            <p className="text-sm font-medium text-ink">
                              {item.start_time && <span className="mr-1.5 font-mono text-meta text-muted-foreground tabular">{item.start_time}</span>}
                              {item.title}
                              {rating != null && <span className="ml-1.5 text-meta text-muted-foreground tabular">★ {rating.toFixed(1)}</span>}
                            </p>
                            {item.note && <p className="text-meta text-muted-foreground">{item.note}</p>}
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                ))}
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
