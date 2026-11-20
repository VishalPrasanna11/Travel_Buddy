import { useEffect, useState } from "react"
import { BedDouble, CloudSun, Landmark, Plane, Utensils } from "lucide-react"

/**
 * Waiting state. The ask endpoint sends only keep-alive bytes until the whole
 * answer is ready, so there is no real per-agent progress to show. This is
 * time-based and honest: it says what is being checked and how long it has
 * been, and never marks a step as finished. (Real progress needs SSE/NDJSON
 * events from the backend; see the report.)
 */
const AGENTS = [
  { label: "Flights", icon: Plane, iconClass: "text-flight-ink", chip: "bg-flight-tint" },
  { label: "Hotels", icon: BedDouble, iconClass: "text-stay-ink", chip: "bg-stay-tint" },
  { label: "Places to see", icon: Landmark, iconClass: "text-raspberry", chip: "bg-raspberry-tint" },
  { label: "Restaurants", icon: Utensils, iconClass: "text-raspberry", chip: "bg-raspberry-tint" },
  { label: "Weather", icon: CloudSun, iconClass: "text-amber-ink", chip: "bg-estimate-tint" },
]

function stageFor(seconds: number) {
  if (seconds < 6) return "Reading your request"
  if (seconds < 30) return "Checking flights, hotels, places and weather"
  if (seconds < 50) return "Putting your itinerary together"
  if (seconds < 90) return "Still working. Bigger trips can take about a minute."
  return "This is taking longer than usual. You can keep waiting; it stops after 2 minutes."
}

function fmt(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

export function AgentProgress({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const seconds = Math.max(0, Math.floor((now - since) / 1000))

  return (
    <div className="max-w-prose animate-fade-in rounded-xl border bg-card p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="font-semibold text-ink">{stageFor(seconds)}</p>
        <span className="shrink-0 font-mono text-meta text-muted-foreground tabular" aria-hidden="true">
          {fmt(seconds)}
        </span>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Most trips take 20–40 seconds. Everything arrives together when it's ready.
      </p>
      <ul className="mt-3 flex flex-wrap gap-2" aria-label="Being checked">
        {AGENTS.map(({ label, icon: Icon, iconClass, chip }) => (
          <li key={label} className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-meta text-ink ${chip}`}>
            <Icon className={`size-3.5 ${iconClass}`} aria-hidden="true" />
            {label}
          </li>
        ))}
      </ul>
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted" aria-hidden="true">
        <div className="h-full w-1/3 rounded-full bg-raspberry/60 motion-safe:animate-[progress-slide_1.6s_cubic-bezier(0.65,0,0.35,1)_infinite]" />
      </div>
    </div>
  )
}
