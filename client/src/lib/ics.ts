import type { Itinerary, ItineraryItem } from "@/components/chat/types"

/**
 * Client-side .ics (RFC 5545) from the structured itinerary. Items without a
 * start time get the slot's usual window (morning 9–12, afternoon 13–17,
 * evening 19–21, night 21–23), in the destination's time zone.
 */
const SLOT_WINDOWS: Record<ItineraryItem["slot"], [string, number]> = {
  morning: ["09:00", 180],
  afternoon: ["13:00", 240],
  evening: ["19:00", 120],
  night: ["21:00", 120],
}

function esc(text: string) {
  return text.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n")
}

/** Fold lines to 75 octets as the spec asks. */
function fold(line: string) {
  const out: string[] = []
  let rest = line
  while (rest.length > 74) {
    out.push(rest.slice(0, 74))
    rest = " " + rest.slice(74)
  }
  out.push(rest)
  return out.join("\r\n")
}

function localStamp(date: string, time: string) {
  return `${date.replace(/-/g, "")}T${time.replace(":", "")}00`
}

function addMinutes(date: string, time: string, minutes: number) {
  const [h, m] = time.split(":").map(Number)
  const total = h * 60 + m + minutes
  const dayShift = Math.floor(total / 1440)
  const mins = total % 1440
  const d = new Date(`${date}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + dayShift)
  const hh = String(Math.floor(mins / 60)).padStart(2, "0")
  const mm = String(mins % 60).padStart(2, "0")
  return localStamp(d.toISOString().slice(0, 10), `${hh}:${mm}`)
}

export function itineraryToIcs(it: Itinerary, opts: { describe?: (item: ItineraryItem) => string | undefined } = {}) {
  const tz = it.trip?.destination?.timezone
  const where = it.trip?.destination?.name ?? ""
  const now = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z")
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//TravelBuddy//Itinerary//EN", "CALSCALE:GREGORIAN", `X-WR-CALNAME:${esc(`Trip to ${where}`)}`]
  if (tz) lines.push(`X-WR-TIMEZONE:${tz}`)
  it.days.forEach((day, di) => {
    day.items.forEach((item, ii) => {
      const [defStart, defLen] = SLOT_WINDOWS[item.slot] ?? SLOT_WINDOWS.morning
      const start = item.start_time && /^\d{2}:\d{2}$/.test(item.start_time) ? item.start_time : defStart
      const len = item.duration_minutes ?? defLen
      const tzParam = tz ? `;TZID=${tz}` : ""
      const desc = [item.note, opts.describe?.(item)].filter(Boolean).join("\n")
      lines.push(
        "BEGIN:VEVENT",
        `UID:${day.date}-${di}-${ii}-${Math.abs(hash(item.title))}@travelbuddy`,
        `DTSTAMP:${now}`,
        `DTSTART${tzParam}:${localStamp(day.date, start)}`,
        `DTEND${tzParam}:${addMinutes(day.date, start, len)}`,
        `SUMMARY:${esc(item.title)}`,
        ...(desc ? [`DESCRIPTION:${esc(desc)}`] : []),
        ...(where ? [`LOCATION:${esc(where)}`] : []),
        "END:VEVENT",
      )
    })
  })
  lines.push("END:VCALENDAR")
  return lines.map(fold).join("\r\n") + "\r\n"
}

function hash(s: string) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return h
}

export function downloadFile(name: string, body: BlobPart, type: string) {
  const url = URL.createObjectURL(new Blob([body], { type }))
  const a = document.createElement("a")
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
