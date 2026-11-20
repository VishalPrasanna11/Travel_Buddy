import { useEffect, useState } from "react"
import { AlertTriangle, BedDouble, Car, Check, CloudSun, Landmark, Loader2, Minus, Plane, Utensils, type LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import type { AgentKey, AgentProgressMap, AgentState } from "./types"

/**
 * Live progress for one answer, driven by `agent` events from the streaming
 * endpoint: "Flights ✓ 3 found · Hotels: searching…". Before the first event
 * arrives (or on the non-streaming fallback) it shows an honest elapsed timer.
 */
const AGENTS: { key: AgentKey; label: string; icon: LucideIcon; iconClass: string }[] = [
  { key: "flights", label: "Flights", icon: Plane, iconClass: "text-flight-ink" },
  { key: "hotels", label: "Hotels", icon: BedDouble, iconClass: "text-stay-ink" },
  { key: "cars", label: "Cars", icon: Car, iconClass: "text-flight-ink" },
  { key: "attractions", label: "Places to see", icon: Landmark, iconClass: "text-raspberry" },
  { key: "restaurants", label: "Restaurants", icon: Utensils, iconClass: "text-raspberry" },
  { key: "weather", label: "Weather", icon: CloudSun, iconClass: "text-amber-ink" },
]

function fmt(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

function stateText(state: AgentState, count?: number, message?: string) {
  switch (state) {
    case "queued": return "waiting"
    case "running": return "searching…"
    case "done": return count != null ? `${count} found` : "done"
    case "empty": return message ? "none found" : "no results"
    case "failed": return "unavailable"
    case "skipped": return message ?? "skipped"
  }
}

function StateIcon({ state }: { state: AgentState }) {
  if (state === "running") return <Loader2 className="size-3.5 motion-safe:animate-spin text-muted-foreground" aria-hidden="true" />
  if (state === "done") return <Check className="size-3.5 text-success-ink" aria-hidden="true" />
  if (state === "failed") return <AlertTriangle className="size-3.5 text-destructive" aria-hidden="true" />
  if (state === "empty" || state === "skipped") return <Minus className="size-3.5 text-muted-foreground" aria-hidden="true" />
  return <span className="size-1.5 rounded-full bg-gray-strong" aria-hidden="true" />
}

function headline(progress: AgentProgressMap, hasText: boolean) {
  if (hasText || progress.compose?.state === "running") return "Writing your answer"
  if (progress.intake?.state === "running" || !progress.intake) return "Reading your request"
  const active = AGENTS.filter((a) => progress[a.key]?.state === "running").map((a) => a.label.toLowerCase())
  if (active.length) return `Checking ${active.join(", ")}`
  return "Putting your trip together"
}

export function AgentProgress({ since, progress, hasText = false, onStop }: { since: number; progress?: AgentProgressMap; hasText?: boolean; onStop?: () => void }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const seconds = Math.max(0, Math.floor((now - since) / 1000))
  const p = progress ?? {}
  const planned = AGENTS.filter((a) => p[a.key])
  const live = Object.keys(p).length > 0

  return (
    <div className={cn("max-w-prose animate-fade-in rounded-xl border bg-card p-4", hasText && "mb-4")}>
      <div className="flex items-baseline justify-between gap-3">
        <p className="font-semibold text-ink" aria-live="polite">{headline(p, hasText)}</p>
        <span className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-meta text-muted-foreground tabular" aria-hidden="true">{fmt(seconds)}</span>
          {onStop && (
            <button type="button" onClick={onStop} className="inline-flex min-h-8 items-center rounded-md px-2 text-sm font-medium text-raspberry hover:bg-accent pointer-coarse:min-h-11">
              Stop
            </button>
          )}
        </span>
      </div>
      {live && planned.length > 0 ? (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Search progress">
          {planned.map(({ key, label, icon: Icon, iconClass }) => {
            const s = p[key]!
            return (
              <li
                key={key}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-meta text-ink transition-colors duration-200",
                  s.state === "done" && "border-leaf-green/40 bg-success-tint",
                  s.state === "failed" && "border-red/30 bg-danger-tint",
                  (s.state === "running" || s.state === "queued") && "bg-muted",
                )}
                title={s.message}
              >
                <Icon className={`size-3.5 ${iconClass}`} aria-hidden="true" />
                <span className="font-medium">{label}</span>
                <StateIcon state={s.state} />
                <span className="text-muted-foreground">{stateText(s.state, s.count, s.message)}</span>
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="mt-1 text-sm text-muted-foreground">
          {live ? "Answering from what I know; no live searches needed." : "Connecting to the planners…"}
        </p>
      )}
      {!hasText && (
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted" aria-hidden="true">
          <div className="h-full w-1/3 rounded-full bg-raspberry/60 motion-safe:animate-[progress-slide_1.6s_cubic-bezier(0.65,0,0.35,1)_infinite]" />
        </div>
      )}
    </div>
  )
}
