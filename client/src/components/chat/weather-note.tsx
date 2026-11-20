import { Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSnow, CloudSun, Sun, type LucideIcon } from "lucide-react"

import { Notice } from "@/components/ui/notice"
import { Badge } from "@/components/ui/badge"
import { weatherOf, type ResponseData, type WeatherDay } from "./types"

/**
 * Weather, honestly. A daily forecast strip (high/low, condition, chance of
 * rain) when OpenWeather returned one; a clear "Estimate" notice when the
 * server flagged the weather as simulated. Numbers are never made up here.
 */

/** OpenWeather condition codes → icon (no text parsing). */
function iconFor(id?: number): { Icon: LucideIcon; tone: string } {
  if (id == null) return { Icon: CloudSun, tone: "text-amber-ink" }
  if (id >= 200 && id < 300) return { Icon: CloudLightning, tone: "text-teal-ink" }
  if (id >= 300 && id < 400) return { Icon: CloudDrizzle, tone: "text-teal-ink" }
  if (id >= 500 && id < 600) return { Icon: CloudRain, tone: "text-teal-ink" }
  if (id >= 600 && id < 700) return { Icon: CloudSnow, tone: "text-teal-ink" }
  if (id >= 700 && id < 800) return { Icon: CloudFog, tone: "text-muted-foreground" }
  if (id === 800) return { Icon: Sun, tone: "text-amber-ink" }
  if (id <= 802) return { Icon: CloudSun, tone: "text-amber-ink" }
  return { Icon: Cloud, tone: "text-muted-foreground" }
}

const SIMULATED = /currently 22°C \(72°F\) with clear skies\. The humidity is around 65% with light winds/i

export function isSimulatedWeather(text: string) {
  return SIMULATED.test(text)
}

function dayLabel(date: string) {
  const d = new Date(`${date}T12:00:00`)
  if (Number.isNaN(d.getTime())) return { weekday: date, day: "" }
  return {
    weekday: d.toLocaleDateString(undefined, { weekday: "short" }),
    day: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
  }
}

function DayCell({ d, unit }: { d: WeatherDay; unit: string }) {
  const { Icon, tone } = iconFor(d.condition_id)
  const { weekday, day } = dayLabel(d.date)
  const pop = d.pop != null ? Math.round(d.pop * 100) : null
  return (
    <li className="flex min-w-[5.25rem] flex-col items-center gap-1 rounded-lg border bg-card px-2 py-2.5 text-center">
      <span className="text-meta font-semibold text-ink">{weekday}</span>
      <span className="text-meta text-muted-foreground">{day}</span>
      <Icon className={`my-0.5 size-6 ${tone}`} aria-hidden="true" />
      <span className="sr-only">{d.condition}</span>
      <span className="tabular text-sm">
        {d.temp_max != null && <span className="font-semibold text-ink">{Math.round(d.temp_max)}{unit}</span>}
        {d.temp_min != null && <span className="text-muted-foreground"> / {Math.round(d.temp_min)}{unit}</span>}
      </span>
      {pop != null && (
        <span className={`text-meta tabular ${pop >= 50 ? "text-teal-ink font-medium" : "text-muted-foreground"}`}>
          <span aria-hidden="true">☂ </span>{pop}%<span className="sr-only"> chance of rain</span>
        </span>
      )}
      {d.kind === "day_summary" && <span className="text-[0.6875rem] text-muted-foreground">outlook</span>}
    </li>
  )
}

export function WeatherNote({ data, answer }: { data?: ResponseData; answer: string }) {
  const fc = weatherOf(data)
  const simulated = fc?.is_simulated || (!fc && isSimulatedWeather(answer))

  if (simulated) {
    return (
      <Notice
        tone="estimate"
        className="mt-6 max-w-prose"
        title={<span className="inline-flex items-center gap-2">Weather <Badge variant="estimate">Estimate</Badge></span>}
        description={`Live weather wasn't available${fc?.location ? ` for ${fc.location}` : ""}, so there's no forecast here. Check a weather service before you pack.`}
      />
    )
  }
  const days = fc?.days ?? []
  if (!fc || !days.length) return null
  const unit = fc.units === "imperial" ? "°F" : "°C"

  return (
    <section aria-label={`Weather forecast for ${fc.location}`} className="mt-6 max-w-3xl">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3">
        <h4 className="flex items-center gap-2 text-heading font-semibold">
          <CloudSun className="size-4 text-amber-ink" aria-hidden="true" />
          Weather
          <span className="text-sm font-normal text-muted-foreground">{fc.location}</span>
        </h4>
        <span className="text-meta text-muted-foreground">Forecast from OpenWeather</span>
      </div>
      <ul className="scroll-thin flex gap-2 overflow-x-auto pb-1">
        {days.map((d) => <DayCell key={d.date} d={d} unit={unit} />)}
      </ul>
      {fc.alerts?.length ? (
        <Notice tone="error" className="mt-3" title={fc.alerts[0].event} description={fc.alerts[0].sender ? `Issued by ${fc.alerts[0].sender}` : undefined} />
      ) : null}
    </section>
  )
}
